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

    # External Portals & Social Forums (Prevents False 0/10 Voids)
    r"\bwikipedia\b",
    r"\byoutube\b",
    r"\breddit\b",
    r"\bquora\b",
    r"\btiktok\b",
    r"\btwitter\b",
    r"\bfacebook\b",
    r"\binstagram\b",
    r"\bpinterest\b",
    r"\bmedium\b",
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

# Universal utility & developer intent tokens (passes multi-vertical queries)
UNIVERSAL_INTENT_TOKENS = [
    # Utilities, Calculators & Tools
    "calculator", "converter", "generator", "template", "checklist", "tracker",
    "builder", "tester", "checker", "maker", "schedule", "estimator", "visualizer",
    "formatter", "parser", "viewer", "timer", "table", "chart",
    # Technical & Developer
    "api", "sdk", "fix", "error", "failed", "cannot", "issue", "bug", "workaround",
    "boilerplate", "docker", "config", "setup", "guide", "tutorial",
    "vs", "difference", "alternative", "benchmark", "middleware", "hook", "component",
    "auth", "token", "jwt", "oauth", "migration", "orm", "query", "database", "stream",
    "cli", "plugin", "extension", "library", "package", "memory", "leak", "timeout",
    "crash", "model", "agent", "rag", "vector", "embed", "llm", "pipeline", "schema",
    "deploy", "cluster", "compose", "server", "cors", "ssl", "cert", "env", "proxy",
    # Business, Legal, Travel & Finance
    "closing cost", "after tax", "mortgage", "loan", "schengen", "visa", "fee",
    "profit margin", "invoice", "receipt", "agreement", "contract"
]

DEV_INTENT_TOKENS = UNIVERSAL_INTENT_TOKENS


class ExclusionShield:
    """
    Exclusion filter to drop queries where indie developers cannot compete with
    authorities or primary brand homepages.
    """

    def __init__(self):
        self.exclusion_regexes = [re.compile(p, re.IGNORECASE) for p in EXCLUSION_PATTERNS]

    def is_navigational_or_corporate(self, query: str, category: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Checks if the query contains navigational, corporate, or shopping tokens."""
        q_lower = query.strip().lower()

        # Utility exemption: queries for calculators, converters, templates, generators never get dropped for pricing/cost/salary
        is_explicit_utility = any(u in q_lower for u in [
            "calculator", "converter", "generator", "template", "checklist", "tracker",
            "schedule", "formula", "builder", "checker", "after tax", "closing cost", "estimate"
        ])

        # Check exclusion patterns
        for pat in self.exclusion_regexes:
            if pat.search(q_lower):
                if is_explicit_utility and pat.pattern in [r"\bpricing\b", r"\bprice\b", r"\bcost\b", r"\bsalary\b"]:
                    continue
                return True, f"Excluded pattern match: '{pat.pattern}'"

        # Check single-word queries (e.g. 'docker', 'groq', 'stripe')
        tokens = [t for t in q_lower.split() if len(t) > 1]
        if len(tokens) <= 1:
            return True, "Query too short / single generic brand token"

        # Check intent: query must have >= 3 words OR contain an explicit high-intent utility
        is_high_intent = any(t in q_lower for t in [
            "calculator", "converter", "generator", "template", "checklist", "tracker",
            "schedule", "formula", "builder", "checker", "error", "workaround", "settlement",
            "affidavit", "exemption", "deduction", "waiver", "dispute"
        ])
        if len(tokens) < 3 and not is_high_intent:
            return True, "Generic 1-2 word head term lacks specific intent"

        # Check for non-ASCII noise
        if re.search(r"[\u4e00-\u9fff]", query):
            return True, "Non-English token detected"

        return False, None

    def should_drop(
        self,
        query: str,
        category: Optional[str] = None,
        serp_results: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[bool, str]:
        """Convenience method returning (should_drop: bool, reason: str)."""
        passed, reason = self.evaluate(query, serp_results=serp_results, category=category)
        return (not passed), reason

    def evaluate(
        self,
        query: str,
        serp_results: Optional[List[Dict[str, str]]] = None,
        category: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Runs the full exclusion shield pipeline.
        Returns (is_passed: bool, reason: str).
        """
        is_bad, reason = self.is_navigational_or_corporate(query, category=category)
        if is_bad:
            return False, f"EXCLUDED: {reason}"

        if serp_results:
            is_inst, reason = self.is_institutional_serp(serp_results)
            if is_inst:
                return False, f"EXCLUDED: {reason}"

            is_vendor, reason = self.is_primary_vendor_monopoly(query, serp_results)
            if is_vendor:
                return False, f"EXCLUDED: {reason}"

        return True, "PASSED: Query represents authentic gap intent"


# Disguised telemetry alias
FilterPipeline = ExclusionShield


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
