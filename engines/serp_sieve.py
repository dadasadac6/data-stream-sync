"""
Free DuckDuckGo HTML SERP Auditor (Dual-Evidence Layer 3A)
Zero-cost, zero-API-key organic SERP screen measuring:
- Exact <title> match voids (0/10 = void, 1/10 = vulnerable, >=4/10 = saturated)
- Root domain mismatches (naked homepages ranking for deep queries)
- Forum / weak platform ranking signals (Reddit, StackOverflow, Quora, Medium)
- Top ranking competitor titles & URLs
"""

import logging
import random
import re
import ssl
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("serp_sieve")

# Create unverified SSL context for macOS certificate compatibility
SSL_CTX = ssl._create_unverified_context()

# Domains that represent user discussion rather than dedicated technical tools/guides
FORUM_AND_WEAK_DOMAINS = [
    "reddit.com",
    "quora.com",
    "medium.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
    "discussions.apple.com",
    "community.cloudflare.com",
    "forum.",
    "community.",
    "answers.microsoft.com",
    "dev.to",
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class SerpSieve:
    def __init__(self):
        pass

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duckduckgo.com/",
        }

    def fetch_serp(self, query: str) -> List[Dict[str, str]]:
        """Fetches top 10 organic results from DuckDuckGo HTML endpoint with anti-rate-limit jitter."""
        time.sleep(random.uniform(0.4, 0.9))
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers=self._get_headers())
        html = ""

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML SERP fetch failed for '{query}': {e}. Trying lite endpoint.")
            # Fallback to lite.duckduckgo.com
            try:
                lite_url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
                lite_req = urllib.request.Request(lite_url, headers=self._get_headers())
                with urllib.request.urlopen(lite_req, context=SSL_CTX, timeout=6) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
            except Exception:
                return []

        # Parse result blocks
        blocks = re.findall(r'<div class="result results_links.*?\">(.*?)</div>\s*</div>', html, re.DOTALL)
        results: List[Dict[str, str]] = []

        for b in blocks[:10]:
            m_url = re.search(r"uddg=([^&]+)", b)
            m_title = re.search(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', b, re.DOTALL)
            m_snippet = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', b, re.DOTALL)

            if m_url and m_title:
                try:
                    real_url = urllib.parse.unquote(m_url.group(1))
                    clean_title = unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip()
                    snippet = unescape(re.sub(r"<[^>]+>", "", m_snippet.group(1))).strip() if m_snippet else ""
                    results.append({"title": clean_title, "url": real_url, "snippet": snippet})
                except Exception:
                    continue

        return results

    def audit_serp(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Calculates SERP Vulnerability metrics:
        - exact_title_matches
        - root_domain_in_top5
        - forum_count
        - top_forum_rank
        - serp_vulnerability_score (0 to 40 pts)
        """
        results = serp_results if serp_results is not None else self.fetch_serp(query)
        q_lower = query.lower().strip()
        q_tokens = [t for t in q_lower.split() if len(t) > 2]

        exact_title_count = 0
        root_domain_count_top5 = 0
        forum_count = 0
        top_forum_rank: Optional[int] = None
        has_stale_content = False

        current_year = 2026
        stale_years = [str(y) for y in range(2015, current_year - 1)]

        for idx, item in enumerate(results):
            rank = idx + 1
            title_lower = item["title"].lower()
            url_lower = item["url"].lower()
            snippet = item.get("snippet", "").lower()

            # 1. Exact or near-exact title match
            if q_lower in title_lower:
                exact_title_count += 1
            elif len(q_tokens) >= 3 and sum(1 for t in q_tokens if t in title_lower) == len(q_tokens):
                # All major tokens appear in title
                exact_title_count += 1

            # 2. Root domain mismatch (naked domain ranking in top 5 for multi-word query)
            if rank <= 5 and len(q_tokens) >= 3:
                try:
                    parsed = urlparse(item["url"])
                    path = parsed.path.strip("/")
                    if not path or path == "":
                        root_domain_count_top5 += 1
                except Exception:
                    pass

            # 3. Forum / Discussion ranking
            is_forum = any(d in url_lower for d in FORUM_AND_WEAK_DOMAINS)
            if is_forum:
                forum_count += 1
                if top_forum_rank is None:
                    top_forum_rank = rank

            # 4. Content freshness check (>2 years old)
            for yr in stale_years:
                if yr in snippet or yr in title_lower:
                    has_stale_content = True
                    break

        # Calculate SERP Vulnerability Points (Max 40 pts according to Master Plan)
        serp_score = 0
        if exact_title_count == 0:
            serp_score += 25  # Zero competitors have targeted this exact phrase
        elif exact_title_count == 1:
            serp_score += 18  # Only 1 competitor, very vulnerable
        elif exact_title_count <= 2:
            serp_score += 10
        elif exact_title_count <= 4:
            serp_score += 5

        # Root domain leak in top 5 (+10 pts)
        if root_domain_count_top5 >= 1:
            serp_score += 10

        # Forum ranking in top 3 gives bonus vulnerability
        if top_forum_rank and top_forum_rank <= 3:
            serp_score = min(40, serp_score + 10)
        elif forum_count >= 1:
            serp_score = min(40, serp_score + 5)

        # Stale content (+5 pts)
        if has_stale_content:
            serp_score = min(40, serp_score + 5)

        top_title = results[0]["title"] if results else ""
        top_url = results[0]["url"] if results else ""

        return {
            "query": query,
            "serp_score": min(40, serp_score),
            "exact_title_matches": exact_title_count,
            "root_domain_in_top5": root_domain_count_top5 > 0,
            "forum_count": forum_count,
            "top_forum_rank": top_forum_rank,
            "has_stale_content": has_stale_content,
            "results_count": len(results),
            "top_competitor_title": top_title,
            "top_competitor_url": top_url,
            "raw_results": results,
        }

    # Alias for convenience
    audit = audit_serp


if __name__ == "__main__":
    sieve = SerpSieve()
    audit = sieve.audit_serp("fastapi jwt refresh token boilerplate")
    print(f"Query: {audit['query']}")
    print(f"SERP Vulnerability Score: {audit['serp_score']}/40")
    print(f"Exact Title Matches: {audit['exact_title_matches']}")
    print(f"Forums in Top 10: {audit['forum_count']}")
    print(f"Top Result: {audit['top_competitor_title']} ({audit['top_competitor_url']})")
