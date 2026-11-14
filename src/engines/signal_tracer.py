"""
Developer Evidence Collectors (Dual-Evidence Layer 3B)
Gathers real developer pain signals from:
1. Stack Exchange API (Unresolved / unaccepted questions on Stack Overflow with strict token overlap matching)
2. GitHub Search API (Open bug/feature issues vs existing dedicated repos)
3. Hacker News Algolia API (Developer discussion velocity & comment volume)
"""

import gzip
import json
import logging
import os
import random
import re
import ssl
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("dev_evidence")

SSL_CTX = ssl._create_unverified_context()

# Load .env file if present in workspace root
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("\"'")
                    if k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        logger.debug(f"Could not load .env file: {e}")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ============================================================
# STRICT TOKEN OVERLAP & RELEVANCE EVALUATION
# ============================================================

_STOPWORDS = frozenset([
    "a", "an", "the", "is", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "with", "this", "that",
    "how", "why", "what", "when", "where", "which", "who",
    "can", "do", "does", "did", "will", "would", "could", "should",
    "has", "have", "had", "be", "been", "are", "was", "were",
    "i", "my", "we", "our", "you", "your", "it", "its",
    "from", "as", "by", "into", "through", "about", "between",
])


def tokenize_for_matching(text: str) -> Set[str]:
    """Lowercases, strips punctuation, removes stopwords, and returns a set of content tokens."""
    tokens = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def compute_token_overlap(query: str, candidate_title: str) -> float:
    """Computes Jaccard similarity between query tokens and candidate title tokens."""
    q_tokens = tokenize_for_matching(query)
    c_tokens = tokenize_for_matching(candidate_title)
    if not q_tokens or not c_tokens:
        return 0.0
    intersection = q_tokens & c_tokens
    union = q_tokens | c_tokens
    return len(intersection) / len(union)


def compute_query_coverage(query: str, candidate_title: str) -> float:
    """Fraction of query tokens that appear in candidate title."""
    q_tokens = tokenize_for_matching(query)
    c_tokens = tokenize_for_matching(candidate_title)
    if not q_tokens:
        return 0.0
    return len(q_tokens & c_tokens) / len(q_tokens)


def is_dev_evidence_relevant(
    query: str,
    result_title: str,
    min_jaccard: float = 0.25,
    min_coverage: float = 0.50,
) -> Tuple[bool, float, float, str]:
    """
    Determines if a StackExchange/GitHub result is genuinely relevant to the query.
    Passes if EITHER Jaccard >= min_jaccard OR coverage >= min_coverage.
    """
    jaccard = compute_token_overlap(query, result_title)
    coverage = compute_query_coverage(query, result_title)

    if jaccard >= min_jaccard:
        return True, jaccard, coverage, f"Jaccard={jaccard:.2f} >= {min_jaccard}"
    if coverage >= min_coverage:
        return True, jaccard, coverage, f"Coverage={coverage:.2f} >= {min_coverage}"

    return (
        False, jaccard, coverage,
        f"Jaccard={jaccard:.2f} < {min_jaccard} AND Coverage={coverage:.2f} < {min_coverage} (Irrelevant)"
    )


def score_stack_exchange_results(
    query: str,
    se_items: List[Dict[str, Any]],
    max_points: int = 15,
    min_jaccard: float = 0.25,
    min_coverage: float = 0.50,
) -> Dict[str, Any]:
    """Filters StackExchange questions against strict phrase overlap thresholds."""
    relevant = []
    irrelevant = []

    for item in se_items:
        title = item.get("title", "")
        is_rel, jac, cov, reason = is_dev_evidence_relevant(
            query, title, min_jaccard, min_coverage
        )
        entry = {
            "title": title,
            "jaccard": round(jac, 3),
            "coverage": round(cov, 3),
            "reason": reason,
            "is_answered": item.get("is_answered", False),
            "answer_count": item.get("answer_count", 0),
            "view_count": item.get("view_count", 0),
        }
        if is_rel:
            relevant.append(entry)
        else:
            irrelevant.append(entry)

    relevant_unresolved = [r for r in relevant if not r["is_answered"] or r["answer_count"] == 0]
    score_contribution = 0

    if len(relevant_unresolved) >= 2:
        score_contribution = max_points  # +15 pts
    elif len(relevant_unresolved) == 1:
        score_contribution = 10  # +10 pts
    elif len(relevant) >= 1:
        score_contribution = 5   # +5 pts for answered relevant questions

    return {
        "dev_score_contribution": score_contribution,
        "relevant_count": len(relevant),
        "irrelevant_count": len(irrelevant),
        "relevant_titles": [r["title"] for r in relevant],
        "sample_relevant_title": relevant[0]["title"] if relevant else "",
        "has_unresolved": len(relevant_unresolved) > 0,
        "relevance_details": relevant[:3],
    }


class DevEvidenceCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "DeveloperSearchGapRadar/3.0 (Autonomous Dev Intel Engine; contact@radar.dev)",
            "Accept": "application/json",
        }
        if GITHUB_TOKEN:
            self.github_headers = {**self.headers, "Authorization": f"Bearer {GITHUB_TOKEN}"}
        else:
            self.github_headers = self.headers

    def _fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        req = urllib.request.Request(url, headers=headers or self.headers)
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as resp:
                raw_bytes = resp.read()
                # Handle Stack Exchange gzip encoding
                if resp.info().get("Content-Encoding") == "gzip" or raw_bytes.startswith(b"\x1f\x8b"):
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                    except Exception:
                        pass
                return json.loads(raw_bytes.decode("utf-8", errors="ignore"))
        except Exception as e:
            logger.debug(f"JSON fetch error for {url}: {e}")
            return None

    def check_stack_exchange(self, query: str) -> Dict[str, Any]:
        """
        Queries Stack Exchange API for unresolved / unaccepted questions on Stack Overflow,
        filtering results through strict token overlap to reject false matches.
        """
        clean_q = " ".join([w for w in query.split() if len(w) > 2][:4])
        url = (
            f"https://api.stackexchange.com/2.3/search/advanced?"
            f"order=desc&sort=relevance&q={urllib.parse.quote(clean_q)}&accepted=False&site=stackoverflow"
        )
        data = self._fetch_json(url)
        if not data or "items" not in data:
            return {
                "unresolved_count": 0,
                "has_unresolved": False,
                "total_items": 0,
                "dev_score_contribution": 0,
                "sample_title": "",
            }

        items = data.get("items", [])
        evaluated = score_stack_exchange_results(query, items)

        return {
            "unresolved_count": evaluated["relevant_count"],
            "total_items": len(items),
            "has_unresolved": evaluated["has_unresolved"],
            "sample_title": evaluated["sample_relevant_title"],
            "dev_score_contribution": evaluated["dev_score_contribution"],
            "details": evaluated,
        }

    def check_github_signals(self, query: str) -> Dict[str, Any]:
        """
        Queries GitHub Search API to compare open issues against existing repositories.
        High open issues + low repositories = classic micro-tool / boilerplate gap.
        """
        clean_q = " ".join([w for w in query.split() if len(w) > 2][:4])

        issues_url = f"https://api.github.com/search/issues?q={urllib.parse.quote(clean_q)}+type:issue+state:open&per_page=10"
        repos_url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(clean_q)}&per_page=10"

        issues_data = self._fetch_json(issues_url, headers=self.github_headers)
        time.sleep(0.2)
        repos_data = self._fetch_json(repos_url, headers=self.github_headers)

        # Filter issues by relevance if returned
        raw_issues = issues_data.get("items", []) if issues_data else []
        relevant_issues = [
            i for i in raw_issues
            if is_dev_evidence_relevant(query, i.get("title", ""))[0]
        ] if raw_issues else []

        open_issues_count = len(relevant_issues) if raw_issues else (issues_data.get("total_count", 0) if issues_data else 0)
        repos_count = repos_data.get("total_count", 0) if repos_data else 0

        # Solution gap exists if open issues significantly outpace repository solutions
        is_solution_gap = open_issues_count >= 5 and (repos_count == 0 or open_issues_count > repos_count * 2)

        return {
            "open_issues_count": open_issues_count,
            "repos_count": repos_count,
            "is_solution_gap": is_solution_gap,
            "has_github_issues": open_issues_count > 0,
        }

    def check_hacker_news(self, query: str) -> Dict[str, Any]:
        """
        Queries Hacker News Algolia API (100% free, unmetered) for community discussions.
        """
        clean_q = " ".join([w for w in query.split() if len(w) > 2][:3])
        url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(clean_q)}&hitsPerPage=5"
        data = self._fetch_json(url)

        if not data or "hits" not in data:
            return {"hn_discussions": 0, "total_comments": 0, "has_sentiment": False}

        hits = data.get("hits", [])
        total_comments = sum(h.get("num_comments", 0) or 0 for h in hits)

        return {
            "hn_discussions": len(hits),
            "total_comments": total_comments,
            "has_sentiment": len(hits) > 0 and total_comments >= 10,
        }

    def collect_evidence(self, query: str) -> Dict[str, Any]:
        """
        Aggregates all 3 developer evidence sources and calculates dev score (0 to 30 pts).
        """
        se = self.check_stack_exchange(query)
        gh = self.check_github_signals(query)
        hn = self.check_hacker_news(query)

        dev_score = 0

        # 1. GitHub Open Issues vs Repos (+20 pts max)
        if gh.get("is_solution_gap"):
            dev_score += 20
        elif gh.get("open_issues_count", 0) >= 3:
            dev_score += 12
        elif gh.get("open_issues_count", 0) >= 1:
            dev_score += 6

        # 2. Stack Overflow Unresolved (Strict relevance scored, +15 pts max)
        dev_score = min(30, dev_score + se.get("dev_score_contribution", 0))

        # 3. Hacker News sentiment (+10 pts max)
        if hn.get("has_sentiment"):
            dev_score = min(30, dev_score + 10)
        elif hn.get("hn_discussions", 0) > 0:
            dev_score = min(30, dev_score + 5)

        return {
            "query": query,
            "dev_score": min(30, dev_score),
            "stack_exchange": se,
            "github": gh,
            "hacker_news": hn,
            "has_stack_questions": se.get("has_unresolved", False),
            "has_github_issues": gh.get("has_github_issues", False),
        }

    collect = collect_evidence


# Disguised telemetry alias
SignalTracer = DevEvidenceCollector


if __name__ == "__main__":
    # Test strict phrase matching
    test_q = "calorie calculator net"
    sample_irrelevant = [{"title": "Copying cell data based on a changing date", "is_answered": False, "answer_count": 0}]
    eval_res = score_stack_exchange_results(test_q, sample_irrelevant)
    print("Dev Relevance Test on False Positive:")
    print(f"Query: {test_q}")
    print(f"Irrelevant Title: {sample_irrelevant[0]['title']}")
    print(f"Score Contribution: {eval_res['dev_score_contribution']} pts (Expected 0)")
    print(f"Relevant count: {eval_res['relevant_count']}")

    test_valid_q = "heic error windows"
    sample_valid = [{"title": "Imagick .heic format not supported in php on windows", "is_answered": False, "answer_count": 0}]
    eval_valid = score_stack_exchange_results(test_valid_q, sample_valid)
    print("\nDev Relevance Test on True Developer Issue:")
    print(f"Query: {test_valid_q}")
    print(f"Candidate Title: {sample_valid[0]['title']}")
    print(f"Score Contribution: {eval_valid['dev_score_contribution']} pts (Expected 10 or 15)")
