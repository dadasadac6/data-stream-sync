"""
Developer Evidence Collectors (Dual-Evidence Layer 3B)
Gathers real developer pain signals from:
1. Stack Exchange API (Unresolved / unaccepted questions on Stack Overflow)
2. GitHub Search API (Open bug/feature issues vs existing dedicated repos)
3. Hacker News Algolia API (Developer discussion velocity & comment volume)
"""

import gzip
import json
import logging
import os
import random
import ssl
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

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
        Queries Stack Exchange API for unresolved / unaccepted questions on Stack Overflow.
        """
        # Focus on core query tokens
        clean_q = " ".join([w for w in query.split() if len(w) > 2][:4])
        url = (
            f"https://api.stackexchange.com/2.3/search/advanced?"
            f"order=desc&sort=relevance&q={urllib.parse.quote(clean_q)}&accepted=False&site=stackoverflow"
        )
        data = self._fetch_json(url)
        if not data or "items" not in data:
            return {"unresolved_count": 0, "has_unresolved": False}

        items = data.get("items", [])
        unresolved = [q for q in items if not q.get("is_answered", False) or q.get("answer_count", 0) == 0]

        return {
            "unresolved_count": len(unresolved),
            "total_items": len(items),
            "has_unresolved": len(unresolved) > 0,
            "sample_title": items[0].get("title") if items else "",
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

        open_issues_count = issues_data.get("total_count", 0) if issues_data else 0
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
            return {"hn_discussions": 0, "total_comments": 0}

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

        # Developer Evidence Points (Max 30 pts according to Master Plan)
        dev_score = 0

        # 1. GitHub Open Issues vs Repos (+20 pts max)
        if gh.get("is_solution_gap"):
            dev_score += 20
        elif gh.get("open_issues_count", 0) >= 3:
            dev_score += 12
        elif gh.get("open_issues_count", 0) >= 1:
            dev_score += 6

        # 2. Stack Overflow Unresolved (+15 pts max)
        if se.get("unresolved_count", 0) >= 3:
            dev_score = min(30, dev_score + 15)
        elif se.get("has_unresolved"):
            dev_score = min(30, dev_score + 10)
        elif se.get("total_items", 0) > 0:
            dev_score = min(30, dev_score + 5)

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

    # Alias for convenience
    collect = collect_evidence


if __name__ == "__main__":
    collector = DevEvidenceCollector()
    res = collector.collect_evidence("ollama cuda out of memory")
    print(f"Evidence for: {res['query']}")
    print(f"Dev Score: {res['dev_score']}/30")
    print(f"Stack Exchange: {res['stack_exchange']}")
    print(f"GitHub: {res['github']}")
    print(f"Hacker News: {res['hacker_news']}")
