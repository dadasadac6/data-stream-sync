"""
Free DuckDuckGo HTML SERP Auditor (Dual-Evidence Layer 3A)
Zero-cost, zero-API-key organic SERP screen measuring:
- Exact <title> match voids (0/10 = void, 1/10 = vulnerable, >=4/10 = saturated)
- Root domain mismatches (naked homepages ranking for deep queries)
- Forum / weak platform ranking signals (Reddit, StackOverflow, Quora, Medium)
- Navigational TLD & brand collision detection (false positive suppression)
- DuckDuckGo sponsored ad stripping
- Top ranking competitor titles & URLs
"""

import logging
import random
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

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

# ============================================================
# AD STRIPPING PATTERNS & UTILITIES
# ============================================================

_DDG_AD_PATTERNS = re.compile(
    r"duckduckgo\.com/y\.js"
    r"|ad_domain="
    r"|ad_provider="
    r"|ad_type="
    r"|click_metadata="
    r"|bingv[0-9]"
    r"|/aclick\?"
    r"|msclkid="
    r"|utm_medium=cpc"
    r"|gclid="
    r"|dclid=",
    re.IGNORECASE,
)

_DDG_AD_CLASSES = re.compile(
    r'class=["\'][^"\']*(?:result--ad|badge--ad|result__sponsored)[^"\']*["\']',
    re.IGNORECASE,
)


def is_ad_url(url: str) -> bool:
    """Returns True if the URL is a sponsored/ad redirect that must be stripped."""
    if not url:
        return False
    return bool(_DDG_AD_PATTERNS.search(url))


def strip_ads_from_results(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Filters a list of SERP result dicts, removing any entry whose URL
    resolves to an ad redirect.
    """
    cleaned = []
    for item in results:
        url = item.get("url", "")
        if is_ad_url(url):
            continue
        # Secondary check: if title is empty AND url contains tracking patterns
        if not item.get("title", "").strip() and "click_metadata" in url:
            continue
        cleaned.append(item)
    return cleaned


def extract_real_url_from_uddg(raw_url: str) -> str:
    """
    Safely extracts the real destination URL from DuckDuckGo's uddg= redirect.
    Handles double-encoding that DDG sometimes applies.
    """
    if "uddg=" in raw_url:
        try:
            parsed = urlparse(raw_url)
            params = parse_qs(parsed.query)
            uddg_vals = params.get("uddg", [])
            if uddg_vals:
                real = unquote(uddg_vals[0])
                if real.startswith("http"):
                    return real
        except Exception:
            pass
    return raw_url


# ============================================================
# NAVIGATIONAL TLD & BRAND COLLISION DETECTOR
# ============================================================

_NAV_TLD_SUFFIXES = frozenset([
    "net", "com", "org", "io", "co", "app", "dev", "ai",
    "gov", "edu", "info", "biz", "us", "uk", "ca", "au",
])

_NAV_INTENT_TOKENS = frozenset([
    "login", "portal", "website", "site", "homepage", "official",
    "download", "sign in", "signup", "register", "account",
    "dashboard", "admin", "console", "status", "support", "help center",
])

_BRAND_ABBREV_MAP = {
    "ms":       ("Microsoft", "microsoft.com"),
    "msft":     ("Microsoft", "microsoft.com"),
    "aws":      ("Amazon Web Services", "amazonaws.com"),
    "amzn":     ("Amazon", "amazon.com"),
    "fb":       ("Facebook/Meta", "facebook.com"),
    "meta":     ("Meta", "meta.com"),
    "goog":     ("Google", "google.com"),
    "yt":       ("YouTube", "youtube.com"),
    "gh":       ("GitHub", "github.com"),
    "npm":      ("NPM", "npmjs.com"),
    "pypi":     ("PyPI", "pypi.org"),
    "so":       ("Stack Overflow", "stackoverflow.com"),
    "wp":       ("WordPress", "wordpress.com"),
    "shopify":  ("Shopify", "shopify.com"),
    "vercel":   ("Vercel", "vercel.com"),
    "netlify":  ("Netlify", "netlify.com"),
    "tf":       ("TensorFlow", "tensorflow.org"),
    "sk":       ("SciKit-Learn", "scikit-learn.org"),
    "hf":       ("HuggingFace", "huggingface.co"),
    "cf":       ("Cloudflare", "cloudflare.com"),
    "do":       ("DigitalOcean", "digitalocean.com"),
    "gcp":      ("Google Cloud", "cloud.google.com"),
    "az":       ("Azure", "azure.microsoft.com"),
    "k8s":      ("Kubernetes", "kubernetes.io"),
    "ts":       ("TypeScript", "typescriptlang.org"),
    "js":       ("JavaScript", "javascript.com"),
    "py":       ("Python", "python.org"),
    "rb":       ("Ruby", "ruby-lang.org"),
    "rs":       ("Rust", "rust-lang.org"),
    "go":       ("Go Lang", "go.dev"),
    "twitch":   ("Twitch", "twitch.tv"),
    "tt":       ("TikTok", "tiktok.com"),
    "li":       ("LinkedIn", "linkedin.com"),
    "wa":       ("WhatsApp", "whatsapp.com"),
    "tg":       ("Telegram", "telegram.org"),
}


def detect_navigational_query(
    query: str,
    serp_results: List[Dict[str, str]],
    tld_collision_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Detects whether a query is navigational (user looking for a specific domain/brand)
    rather than informational/transactional, which would invalidate a "void" finding.
    """
    q_lower = query.lower().strip()
    q_tokens = q_lower.split()
    result = {
        "is_navigational": False,
        "confidence": 0.0,
        "reason": "",
        "nav_type": "",
        "penalty_points": 0,
    }

    # --- Check 1: Query ends with a TLD token (e.g. "calorie calculator net") ---
    last_token = q_tokens[-1] if q_tokens else ""
    if last_token in _NAV_TLD_SUFFIXES:
        tld_hits = sum(
            1 for r in serp_results
            if f".{last_token}" in urlparse(r.get("url", "")).netloc.lower()
        )
        ratio = tld_hits / max(len(serp_results), 1)
        if ratio >= tld_collision_threshold:
            result.update({
                "is_navigational": True,
                "confidence": min(1.0, ratio),
                "reason": (
                    f"Query ends with '.{last_token}' and {tld_hits}/{len(serp_results)} "
                    f"SERP domains contain '.{last_token}' — navigational domain collision."
                ),
                "nav_type": "tld_collision",
                "penalty_points": 40,  # Completely neutralizes the void SERP score
            })
            return result

    # --- Check 2: Query contains explicit navigational intent tokens ---
    for token in _NAV_INTENT_TOKENS:
        if re.search(r"\b" + re.escape(token) + r"\b", q_lower):
            result.update({
                "is_navigational": True,
                "confidence": 0.75,
                "reason": f"Query contains navigational intent token: '{token}'.",
                "nav_type": "intent_token",
                "penalty_points": 25,
            })
            return result

    # --- Check 3: Brand abbreviation in query tokens ---
    for token in q_tokens:
        if token in _BRAND_ABBREV_MAP:
            brand_name, domain_frag = _BRAND_ABBREV_MAP[token]
            brand_hits = sum(
                1 for r in serp_results
                if domain_frag in r.get("url", "").lower()
            )
            if brand_hits >= 2:
                result.update({
                    "is_navigational": True,
                    "confidence": min(1.0, brand_hits / 5.0),
                    "reason": (
                        f"Token '{token}' maps to brand '{brand_name}' "
                        f"and {brand_hits} SERP results point to its domain."
                    ),
                    "nav_type": "brand_abbrev",
                    "penalty_points": 20,
                })
                return result

    # --- Check 4: Explicit domain name in query (e.g. "calculator.net", "github.com") ---
    domain_in_query = re.search(
        r'\b[a-z0-9\-]+\.(com|net|org|io|co|app|dev|ai|gov|edu)\b',
        q_lower,
    )
    if domain_in_query:
        result.update({
            "is_navigational": True,
            "confidence": 0.95,
            "reason": f"Query contains a full domain pattern: '{domain_in_query.group(0)}'.",
            "nav_type": "explicit_domain",
            "penalty_points": 40,
        })
        return result

    return result


def apply_navigational_penalty(serp_result: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Applies navigational penalty to serp_score and records audit signals."""
    nav = detect_navigational_query(
        query=query,
        serp_results=serp_result.get("raw_results", []),
    )
    serp_result["navigational_signal"] = nav
    if nav["is_navigational"]:
        old_score = serp_result.get("serp_score", 0)
        serp_result["serp_score"] = max(0, old_score - nav["penalty_points"])
        serp_result["navigational_penalty_applied"] = nav["penalty_points"]
        serp_result["navigational_reason"] = nav["reason"]
    return serp_result


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
        """
        Fetches top 10 organic results from DuckDuckGo HTML endpoint,
        falling back to lite.duckduckgo.com if primary fails or is rate-limited.
        Strips all sponsored ads and tracks destination URLs cleanly.
        """
        time.sleep(random.uniform(0.3, 0.7))
        results: List[Dict[str, str]] = []

        # 1. Primary: html.duckduckgo.com
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            blocks = re.findall(r'<div class="result results_links.*?\">(.*?)</div>\s*</div>', html, re.DOTALL)
            for b in blocks:
                # Skip sponsored / ad divs
                if _DDG_AD_CLASSES.search(b):
                    continue

                m_url = re.search(r"uddg=([^&]+)", b)
                m_title = re.search(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', b, re.DOTALL)
                m_snippet = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', b, re.DOTALL)

                if m_url and m_title:
                    try:
                        raw_href = urllib.parse.unquote(m_url.group(1))
                        real_url = extract_real_url_from_uddg(raw_href)
                        if is_ad_url(real_url):
                            continue
                        clean_title = unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip()
                        snippet = unescape(re.sub(r"<[^>]+>", "", m_snippet.group(1))).strip() if m_snippet else ""
                        results.append({"title": clean_title, "url": real_url, "snippet": snippet})
                    except Exception:
                        continue
            results = strip_ads_from_results(results)
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML SERP primary fetch failed for '{query}': {e}")

        # 2. Resilient Fallback: lite.duckduckgo.com
        if not results:
            try:
                lite_url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
                lite_req = urllib.request.Request(lite_url, headers=self._get_headers())
                with urllib.request.urlopen(lite_req, context=SSL_CTX, timeout=5) as resp:
                    lite_html = resp.read().decode("utf-8", errors="ignore")

                matches = re.findall(r'<a\s+[^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*class=[\'\"]result-link[\'\"][^>]*>(.*?)</a>', lite_html, re.DOTALL)
                for href, title in matches:
                    if "duckduckgo-help-pages" in href or "more info" in title.lower() or is_ad_url(href):
                        continue
                    m = re.search(r"uddg=([^&]+)", href)
                    real_url = urllib.parse.unquote(m.group(1)) if m else href
                    real_url = extract_real_url_from_uddg(real_url)
                    if is_ad_url(real_url):
                        continue
                    clean_title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
                    results.append({"title": clean_title, "url": real_url, "snippet": ""})
                results = strip_ads_from_results(results)
            except Exception as e:
                logger.debug(f"DuckDuckGo Lite fallback fetch failed for '{query}': {e}")

        return results[:10]

    def audit(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Convenience alias for audit_serp."""
        return self.audit_serp(query, serp_results=serp_results)

    def audit_serp(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Calculates SERP Vulnerability metrics:
        - exact_title_matches
        - root_domain_in_top5
        - forum_count
        - top_forum_rank
        - serp_vulnerability_score (0 to 40 pts)
        - navigational penalty application
        """
        raw = serp_results if serp_results is not None else self.fetch_serp(query)
        results = strip_ads_from_results(raw)[:10]

        # Guard: If no results could be retrieved, do NOT claim untouched void!
        if not results:
            return {
                "query": query,
                "serp_score": 0,
                "exact_title_matches": None,
                "root_domain_in_top5": False,
                "forum_count": 0,
                "top_forum_rank": None,
                "has_stale_content": False,
                "results_count": 0,
                "top_competitor_title": "",
                "top_competitor_url": "",
                "raw_results": [],
                "navigational_signal": {"is_navigational": False},
            }

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

        # Calculate SERP Vulnerability Points (Max 40 pts)
        serp_score = 0
        if exact_title_count == 0:
            serp_score += 25
        elif exact_title_count == 1:
            serp_score += 18
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

        output = {
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

        # Apply navigational penalty
        output = apply_navigational_penalty(output, query)
        return output

    audit = audit_serp


# Disguised telemetry alias
IndexAuditor = SerpSieve


if __name__ == "__main__":
    sieve = SerpSieve()
    # Test navigational query
    test_nav = sieve.audit_serp(
        "calorie calculator net",
        serp_results=[
            {"title": "Calorie Calculator", "url": "https://www.calculator.net/calorie-calculator.html"},
            {"title": "Calorie Calculator", "url": "https://www.calculator.net/calorie-intake-calculator.html"},
            {"title": "Calorie King", "url": "https://www.calorieking.com"},
            {"title": "MyFitnessPal", "url": "https://www.myfitnesspal.com"},
            {"title": "Body Fat Calculator", "url": "https://www.calculator.net/body-fat-calculator.html"},
            {"title": "Macro Calculator", "url": "https://www.calculator.net/macro-calculator.html"},
        ]
    )
    print("Navigational Test:")
    print(f"Query: {test_nav['query']}")
    print(f"SERP Vulnerability Score: {test_nav['serp_score']}/40 (Expected 0 due to penalty)")
    print(f"Is Navigational: {test_nav['navigational_signal']['is_navigational']}")
    print(f"Reason: {test_nav['navigational_signal']['reason']}")
