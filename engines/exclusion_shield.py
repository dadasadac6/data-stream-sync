"""
Authority & Navigational Exclusion Shield
Protects the radar against unwinnable competition by filtering out:
1. Institutional domains (.gov, .edu, .mil, standards bodies)
2. Navigational brand queries (login, portal, careers, support, pricing)
3. Canonical primary vendor documentation rankings
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Navigational intent tokens that signal official account/portal searches
NAVIGATIONAL_TOKENS = [
    r"\blogin\b",
    r"\bsignin\b",
    r"\bsign up\b",
    r"\bportal\b",
    r"\bcareers?\b",
    r"\bjobs?\b",
    r"\bsupport number\b",
    r"\bcustomer care\b",
    r"\bofficial site\b",
    r"\bofficial website\b",
    r"\bterms of service\b",
    r"\bprivacy policy\b",
    r"\bcontact us\b",
    r"\bpricing plans?\b",
    r"\bstatus page\b",
    r"\bheadquarters\b",
    r"\bwikipedia\b",
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


class ExclusionShield:
    """
    Exclusion filter to drop queries where indie developers cannot compete with
    authorities or primary brand homepages.
    """

    def __init__(self):
        self.nav_patterns = [re.compile(p, re.IGNORECASE) for p in NAVIGATIONAL_TOKENS]

    def is_navigational_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Checks if the query contains brand navigational tokens."""
        q_lower = query.strip().lower()

        # Check for navigational tokens
        for pat in self.nav_patterns:
            if pat.search(q_lower):
                return True, f"Navigational intent detected matching pattern '{pat.pattern}'"

        # Check single-word queries (too broad / informational brand)
        tokens = [t for t in q_lower.split() if len(t) > 1]
        if len(tokens) <= 1:
            return True, "Query too short / generic single token"

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

        # If query has primary brand name in top URL host and top title has exact query
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
        # Step 1: Navigational check
        is_nav, reason = self.is_navigational_query(query)
        if is_nav:
            return False, f"EXCLUDED: {reason}"

        # Step 2: SERP Institutional check (if SERP is provided)
        if serp_results:
            is_inst, reason = self.is_institutional_serp(serp_results)
            if is_inst:
                return False, f"EXCLUDED: {reason}"

            is_vendor, reason = self.is_primary_vendor_monopoly(query, serp_results)
            if is_vendor:
                return False, f"EXCLUDED: {reason}"

        return True, "PASSED: Query represents open user intent"


if __name__ == "__main__":
    shield = ExclusionShield()
    test_queries = [
        "docker login error",
        "supabase login",
        "stripe",
        "fastapi jwt refresh token boilerplate",
        "how to fix ollama cuda out of memory",
    ]
    for q in test_queries:
        passed, reason = shield.evaluate(q)
        print(f"[{'PASS' if passed else 'DROP'}] '{q}': {reason}")
