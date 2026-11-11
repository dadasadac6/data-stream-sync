"""
Authority & Navigational Exclusion Shield (Enhanced v3.1)
Filters out:
1. Brand navigational queries (login, pricing, download, careers, support)
2. Corporate gossip / informational queries (founders, valuation, ceo, salary, revenue)
3. Consumer hardware & shopping queries (best laptop, buy, coupon, store)
4. Institutional domains (.gov, .edu, .mil, standards bodies)
5. Vendor monopolies (e.g. brand.com/docs ranking #1 with exact match)
Ensures only authentic technical developer gaps pass through.
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Navigational, corporate, and consumer intent patterns to drop
EXCLUSION_PATTERNS = [
    # Auth & Account Navigation
    r"\blogin\b",
    r"\bsignin\b",
    r"\bsign up\b",
    r"\bportal\b",
    r"\bmy account\b",
    r"\bdashboard login\b",

    # Corporate & Financial Info (Non-developable)
    r"\bpricing\b",
    r"\bprice\b",
    r"\bplans?\b",
    r"\bcost\b",
    r"\bvaluation\b",
    r"\bnet worth\b",
    r"\brevenue\b",
    r"\bfounding\b",
    r"\bfounders?\b",
    r"\bowner\b",
    r"\bceo\b",
    r"\bwho owns\b",
    r"\bsalary\b",
    r"\bstock\b",
    r"\bmarket cap\b",
    r"\bcompetitors analysis\b",
    r"\bheadquarters\b",

    # Jobs & HR
    r"\bcareers?\b",
    r"\bjobs?\b",
    r"\bhiring\b",
    r"\binternships?\b",
    r"\bglassdoor\b",

    # Official Support & Contacts
    r"\bsupport number\b",
    r"\bcustomer (service|care|support)\b",
    r"\bphone number\b",
    r"\bofficial (site|website)\b",
    r"\bterms of (service|use)\b",
    r"\bprivacy policy\b",
    r"\bcontact us\b",
    r"\bstatus page\b",

    # Binary Downloads / Consumer Store
    r"\bdownloads?\b",
    r"\binstaller\b",
    r"\bcrack\b",
    r"\btorrent\b",
    r"\bcoupon\b",
    r"\bpromo code\b",
    r"\bdiscount\b",
    r"\bbuy\b",
    r"\blaptop\b",
    r"\bpc\b",
    r"\bfree trial\b",
    r"\bapp store\b",
    r"\bgoogle play\b",

    # External Portals
    r"\bwikipedia\b",
    r"\byoutube\b",
]

# Institutional TLDs where official authority dominates SERPs
INSTITUTIONAL_TLDS = [".gov", ".edu", ".mil", ".ac.uk", ".gov.uk", ".edu.au", ".nic.in"]

# Official standards and academic authorities
STANDARDS_BODIES = [
    "ietf.org",
    "w3.org",
    "iso.org",
    "nist.gov",
    "ieee.org",
    "arxiv.org",
    "acm.org",
    "rfc-editor.org",
]

# Positive developer technical intent tokens (at least one should match or length >= 3 tokens)
DEV_INTENT_TOKENS = [
    "api", "sdk", "fix", "error", "failed", "cannot", "issue", "bug", "workaround",
    "boilerplate", "template", "docker", "config", "setup", "guide", "tutorial",
    "vs", "difference", "alternative", "benchmark", "middleware", "hook", "component",
    "auth", "token", "jwt", "oauth", "migration", "orm", "query", "database", "stream",
    "cli", "plugin", "extension", "library", "package", "memory", "leak", "timeout",
    "crash", "model", "agent", "rag", "vector", "embed", "llm", "pipeline", "schema",
    "deploy", "cluster", "compose", "server", "cors", "ssl", "cert", "env", "proxy"
]


class ExclusionShield:
    """
    Exclusion filter to drop queries where indie developers cannot compete with
    authorities or primary brand homepages.
    """

    def __init__(self):
        self.exclusion_regexes = [re.compile(p, re.IGNORECASE) for p in EXCLUSION_PATTERNS]

    def is_navigational_or_corporate(self, query: str) -> Tuple[bool, Optional[str]]:
        """Checks if the query contains navigational, corporate, or shopping tokens."""
        q_lower = query.strip().lower()

        # Check exclusion patterns
        for pat in self.exclusion_regexes:
            if pat.search(q_lower):
                return True, f"Excluded pattern match: '{pat.pattern}'"

        # Check single-word queries (e.g. 'docker', 'groq', 'stripe')
        tokens = [t for t in q_lower.split() if len(t) > 1]
        if len(tokens) <= 1:
            return True, "Query too short / single generic brand token"

        # Check developer relevance: query must have technical relevance or >= 3 words
        has_dev_token = any(t in q_lower for t in DEV_INTENT_TOKENS)
        if not has_dev_token and len(tokens) < 3:
            return True, "Lacks developer technical intent"

        # Check for non-ASCII noise (e.g. Chinese characters if unexpected)
        if re.search(r"[\u4e00-\u9fff]", query):
            return True, "Non-English token detected"

        return False, None

    def is_institutional_serp(self, serp_results: List[Dict[str, str]]) -> Tuple[bool, Optional[str]]:
        """
        Drops queries where institutional domains (.gov, .edu, .mil)
        or standards bodies rank in the top 3 positions.
        """
        if not serp_results:
            return False, None

        for idx, result in enumerate(serp_results[:3]):
            url = result.get("url", "").lower()
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname or ""
            except Exception:
                continue

            for tld in INSTITUTIONAL_TLDS:
                if hostname.endswith(tld):
                    return True, f"Top result #{idx+1} is institutional ({hostname})"

            for std in STANDARDS_BODIES:
                if std in hostname:
                    return True, f"Top result #{idx+1} is a standards body ({hostname})"

        return False, None

    def is_primary_vendor_monopoly(self, query: str, serp_results: List[Dict[str, str]]) -> Tuple[bool, Optional[str]]:
        """
        If a query is for a specific framework or tool (e.g. 'Stripe webhook verification'),
        and the primary vendor (stripe.com) already owns #1 with an exact docs match,
        it's saturated and not worth duplicating.
        """
        if not serp_results:
            return False, None

        top = serp_results[0]
        top_url = top.get("url", "").lower()
        top_title = top.get("title", "").lower()
        q_tokens = [t for t in query.lower().split() if len(t) > 2]

        if len(q_tokens) >= 2:
            brand_token = q_tokens[0]
            if brand_token in top_url and all(t in top_title for t in q_tokens[:3]):
                return True, f"Primary vendor monopoly by {top_url}"

        return False, None

    def evaluate(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Tuple[bool, str]:
        """
        Runs the full exclusion shield pipeline.
        Returns (is_passed: bool, reason: str).
        """
        is_bad, reason = self.is_navigational_or_corporate(query)
        if is_bad:
            return False, f"EXCLUDED: {reason}"

        if serp_results:
            is_inst, reason = self.is_institutional_serp(serp_results)
            if is_inst:
                return False, f"EXCLUDED: {reason}"

            is_vendor, reason = self.is_primary_vendor_monopoly(query, serp_results)
            if is_vendor:
                return False, f"EXCLUDED: {reason}"

        return True, "PASSED: Query represents authentic developer gap intent"


if __name__ == "__main__":
    shield = ExclusionShield()
    test_queries = [
        "cursor ai pricing",
        "cursor ai founders",
        "best laptop for work",
        "huggingface 事件",
        "docker login error",
        "fastapi jwt refresh token boilerplate",
        "difference between langchain and langgraph",
        "ollama cuda out of memory fix",
        "victoria metrics vs prometheus"
    ]
    for q in test_queries:
        passed, reason = shield.evaluate(q)
        print(f"[{'PASS' if passed else 'DROP'}] '{q}': {reason}")
