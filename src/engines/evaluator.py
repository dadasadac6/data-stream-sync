"""
Mathematical Scoring & Archetype Classification Engine
Calculates the 0-100 Composite Opportunity Score based on:
  Final Gap Score = S_SERP (0-40) + S_Dev (0-30) + S_Velocity (0-30)
Maps qualified opportunities into 8 Developable Archetypes:
  1. Micro-Tool
  2. Config Generator
  3. Cost Estimator
  4. Workaround
  5. Compliance Checklist
  6. Interactive Visualizer
  7. Breaking News
  8. Recipe
Includes 3-Layer Zero-Cost Vertical Classification (Tokens + SERP Domains).
Enforces hard caps on navigational searches and unaudited results.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("evaluator")

# ============================================================
# 8 DEVELOPABLE ARCHETYPES (2026 REVENUE MAP)
# ============================================================

ARCHETYPE_RULES = [
    {
        "archetype": "Micro-Tool",
        "description": "Single-page responsive web utility, calculator, or formatter with programmatic SEO",
        "revenue_tier": "A",
        "keywords": [
            "calculator", "converter", "generator", "viewer", "validator",
            "formatter", "tester", "playground", "diff", "visualizer",
            "parser", "decoder", "encoder", "builder", "checker", "linter",
            "mock", "sandbox", "minifier", "beautifier", "editor", "tool",
            "counter", "timer", "tracker", "planner", "scheduler",
        ],
    },
    {
        "archetype": "Config Generator",
        "description": "Interactive configuration file/snippet generator for DevOps, cloud, or framework tooling",
        "revenue_tier": "A",
        "keywords": [
            "config generator", "yaml generator", "dockerfile", "compose",
            "nginx config", "kubernetes yaml", "terraform", "github actions",
            "eslint config", "tsconfig", "webpack config", "vite config",
            "cron expression", "regex generator", "json schema generator",
            "ssl certificate", "ssh config", ".env", "environment variables",
            "cors settings", "htaccess generator", "robots.txt generator",
        ],
    },
    {
        "archetype": "Cost Estimator",
        "description": "Interactive cost/fee/pricing estimator with affiliate or lead-gen potential",
        "revenue_tier": "A",
        "keywords": [
            "cost estimator", "fee calculator", "price calculator", "pricing",
            "aws cost", "gcp cost", "azure cost", "hosting cost",
            "shipping cost", "customs duty", "import tax", "tariff",
            "contractor rate", "freelance rate", "agency cost",
            "legal fees", "closing costs", "moving cost", "remodel cost",
        ],
    },
    {
        "archetype": "Workaround",
        "description": "Definitive troubleshooting guide with verified code snippets and patch scripts",
        "revenue_tier": "B",
        "keywords": [
            "how to fix", "error", "failed to", "cannot resolve", "loop",
            "bypass", "patch", "mismatch", "unexpected", "crash",
            "timeout", "connection refused", "out of memory", "killed",
            "not working", "unable to", "issue", "bug", "exception",
            "unhandled", "denied", "forbidden", "broken", "hangs",
            "won't start", "not loading", "stuck", "corrupted",
        ],
    },
    {
        "archetype": "Compliance Checklist",
        "description": "Interactive compliance checklist, audit template, or regulatory readiness tool",
        "revenue_tier": "B",
        "keywords": [
            "gdpr checklist", "hipaa checklist", "soc2 checklist",
            "iso 27001", "pci dss", "ccpa", "accessibility checklist",
            "wcag checklist", "security audit", "code review checklist",
            "deployment checklist", "legal compliance", "tax compliance",
            "aml checklist", "kyc checklist", "regulatory", "compliance",
        ],
    },
    {
        "archetype": "Interactive Visualizer",
        "description": "Data visualization, chart, or interactive explainer with embed/share potential",
        "revenue_tier": "B",
        "keywords": [
            "visualizer", "chart", "graph", "timeline", "heatmap",
            "comparison chart", "diagram", "flowchart", "dependency graph",
            "network graph", "treemap", "sankey", "gantt",
            "data visualization", "interactive chart", "plot", "dashboard",
        ],
    },
    {
        "archetype": "Breaking News",
        "description": "Rapid technical migration brief, changelog breakdown, or compatibility guide",
        "revenue_tier": "C",
        "keywords": [
            "release date", "what is new", "breaking changes", "migration from",
            "deprecation", "roadmap", "benchmark", "announcement", "v2",
            "v3", "v4", "v5", "2026", "2025", "changelog", "update",
            "end of life", "eol", "sunsetting",
        ],
    },
    {
        "archetype": "Recipe",
        "description": "GitHub starter repository, 1-click template, or copy-paste reference cheatsheet",
        "revenue_tier": "C",
        "keywords": [
            "boilerplate", "starter", "template", "cheatsheet", "best practices",
            "docker compose for", "config for", "example", "setup",
            "integration", "reference", "guide", "pattern",
            "architecture", "scaffold", "stack", "quickstart", "how to use",
        ],
    },
]

# ============================================================
# THREE-LAYER ZERO-COST VERTICAL CLASSIFIER
# ============================================================

_VERTICAL_KEYWORD_MAP = {
    "Finance & Wealth": [
        "tax", "mortgage", "loan", "interest rate", "salary", "paycheck",
        "stock", "crypto", "bitcoin", "portfolio", "dividend", "401k", "ira",
        "budget", "debt", "credit score", "net worth", "roi", "compound interest",
        "forex", "exchange rate", "amortization", "capital gains", "roth",
        "refinance", "heloc", "nps", "ups pension", "mutual fund", "etf",
    ],
    "Small Business & B2B": [
        "invoice", "receipt", "paystub", "nda", "contract template", "proposal",
        "quote template", "purchase order", "break even", "profit margin",
        "llc", "incorporation", "ein", "business license", "accounts receivable",
        "accounts payable", "cash flow", "b2b", "crm", "lead generation",
    ],
    "Productivity & Work": [
        "timesheet", "gantt", "kanban", "pomodoro", "standup", "okr",
        "meeting notes", "agenda template", "workflow", "automation",
        "cron", "scheduler", "reminder", "todo list", "habit tracker",
        "markdown editor", "flowchart", "org chart", "retrospective",
    ],
    "Media & Converters": [
        "convert", "converter", "heic", "webp", "png", "jpg", "jpeg", "gif",
        "mp4", "mp3", "wav", "flac", "pdf", "epub", "svg", "compress",
        "resize", "thumbnail", "audio", "video", "image format",
        "subtitle", "transcribe", "extract audio", "trim video",
    ],
    "Health & Fitness": [
        "calorie", "macro", "bmi", "tdee", "protein", "carbs", "fat",
        "workout", "exercise", "rep", "set", "weight loss", "muscle",
        "keto", "intermittent fasting", "sleep", "water intake",
        "heart rate", "vo2 max", "one rep max", "pace calculator",
        "ovulation", "pregnancy", "body fat", "running",
    ],
    "Real Estate & Living": [
        "mortgage", "rent", "lease", "landlord", "tenant", "property",
        "real estate", "home", "house", "apartment", "closing cost",
        "square footage", "moving", "renovation", "sublet", "roommate",
        "property tax", "hoa", "home inspection", "deed",
    ],
    "Legal & Compliance": [
        "affidavit", "power of attorney", "nda", "contract", "agreement",
        "terms of service", "privacy policy", "gdpr", "hipaa", "trademark",
        "copyright", "cease and desist", "legal", "lawsuit", "litigation",
        "compliance", "regulation", "statute", "ordinance", "subpoena",
        "eviction notice", "disclaimer", "cookie policy",
    ],
    "Academic & Education": [
        "gpa", "grade", "assignment", "thesis", "citation", "plagiarism",
        "essay", "word count", "academic", "university", "college",
        "sat", "gre", "act", "exam", "quiz", "flashcard", "study",
        "bibliography", "apa", "mla", "chicago format", "research paper",
    ],
    "Developer & Cloud": [
        "docker", "kubernetes", "k8s", "api", "rest", "graphql", "webhook",
        "fastapi", "django", "flask", "express", "react", "nextjs", "vue",
        "angular", "typescript", "javascript", "python", "rust", "golang",
        "aws", "gcp", "azure", "terraform", "ansible", "ci/cd", "git",
        "npm", "pip", "package", "library", "framework", "boilerplate",
        "jwt", "oauth", "ssl", "tls", "nginx", "redis", "postgres",
        "mongodb", "sqlite", "supabase", "firebase", "cron job",
        "regex", "json schema", "yaml", "toml", "env file", "ollama",
        "error", "generation error", "runtime", "exception", "debug",
    ],
    "Gaming & Entertainment": [
        "pokemon", "minecraft", "roblox", "steam", "game", "fps",
        "dps", "damage", "weapon", "build", "tier list", "speedrun",
        "mod", "cheat code", "walkthrough", "discord bot", "emulator",
        "mouse sensitivity", "crosshair", "keybind", "aim trainer",
        "wordle", "nyt games", "chess", "esports",
    ],
    "E-Commerce & Selling": [
        "etsy", "ebay", "amazon", "shopify", "woocommerce", "stripe",
        "paypal", "fee calculator", "shipping", "fulfillment", "fba",
        "dropshipping", "print on demand", "listing", "product",
        "inventory", "barcode", "sku", "returns", "refund", "merch",
        "mercari", "poshmark", "depop", "resell",
    ],
    "Travel & Visas": [
        "visa", "passport", "immigration", "flight", "hotel", "airbnb",
        "travel", "customs", "currency", "exchange rate", "packing",
        "schengen", "tourist", "destination", "itinerary", "layover",
        "jet lag", "travel insurance", "backpacking", "hostel",
    ],
}

_DOMAIN_VERTICAL_MAP = {
    "nerdwallet.com": "Finance & Wealth",
    "investopedia.com": "Finance & Wealth",
    "bankrate.com": "Finance & Wealth",
    "calculator.net": "Health & Fitness",
    "mayoclinic.org": "Health & Fitness",
    "healthline.com": "Health & Fitness",
    "myfitnesspal.com": "Health & Fitness",
    "github.com": "Developer & Cloud",
    "stackoverflow.com": "Developer & Cloud",
    "npmjs.com": "Developer & Cloud",
    "docs.python.org": "Developer & Cloud",
    "developer.mozilla.org": "Developer & Cloud",
    "kubernetes.io": "Developer & Cloud",
    "reddit.com/r/learnprogramming": "Developer & Cloud",
    "reddit.com/r/webdev": "Developer & Cloud",
    "etsy.com": "E-Commerce & Selling",
    "shopify.com": "E-Commerce & Selling",
    "amazon.com": "E-Commerce & Selling",
    "zillow.com": "Real Estate & Living",
    "realtor.com": "Real Estate & Living",
}


def classify_vertical_by_tokens(query: str) -> Optional[str]:
    """Layer 1: Fast token-based vertical classification."""
    q_lower = query.lower()
    scores = {}
    for vertical, keywords in _VERTICAL_KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", q_lower))
        if score > 0:
            scores[vertical] = score
    if not scores:
        return None
    best = max(scores, key=lambda k: scores[k])
    second_best_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    if scores[best] - second_best_score >= 1 or scores[best] >= 2:
        return best
    return None


def classify_vertical_by_serp_domains(serp_results: List[Dict[str, Any]]) -> Optional[str]:
    """Layer 2: Classify based on what category of authority sites rank in the SERP."""
    domain_votes: Dict[str, int] = {}
    for result in serp_results[:5]:
        url = result.get("url", "").lower()
        for domain, vertical in _DOMAIN_VERTICAL_MAP.items():
            if domain in url and vertical:
                domain_votes[vertical] = domain_votes.get(vertical, 0) + 1
    if domain_votes:
        return max(domain_votes, key=domain_votes.get)
    return None


def classify_vertical(
    query: str,
    serp_results: Optional[List[Dict[str, Any]]] = None,
    parent_category: Optional[str] = None,
) -> str:
    """
    Three-layer vertical classification:
    Layer 1: Token matching (fastest, most reliable)
    Layer 2: SERP domain analysis (when Layer 1 is ambiguous)
    Layer 3: Parent category fallback (with sanity check)
    """
    # Layer 1
    result = classify_vertical_by_tokens(query)
    if result:
        return result

    # Layer 2
    if serp_results:
        result = classify_vertical_by_serp_domains(serp_results)
        if result:
            return result

    # Layer 3
    if parent_category and parent_category in _VERTICAL_KEYWORD_MAP:
        return parent_category

    return "Developer & Cloud"


def classify_archetype(query: str) -> Tuple[str, str]:
    """
    Classifies a search query into one of the 8 Developable Archetypes.
    Returns (archetype_name, deliverable_description).
    """
    q_lower = query.lower()

    for rule in ARCHETYPE_RULES:
        for kw in rule["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower) or kw in q_lower:
                return rule["archetype"], rule["description"]

    # Fallback heuristics
    if q_lower.startswith("how to") or "fix" in q_lower or "error" in q_lower:
        return "Workaround", "Definitive troubleshooting guide with verified code snippets and patch scripts"

    return "Recipe", "Developer boilerplate, reference recipe, or cheatsheet"


def calculate_velocity_score(trend_type: str, trend_velocity: str) -> int:
    """
    Calculates Trend Velocity Score (0 to 30 pts):
    +30 pts: Breakout (>5,000% surge)
    +20 pts: Rising (+300% to +4,900%)
    +10 pts: Rising (+100% to +299%)
    +05 pts: Top query (stable established volume)
    """
    t_type = trend_type.upper()
    vel_str = str(trend_velocity).upper()

    if t_type == "BREAKOUT" or "BREAKOUT" in vel_str:
        return 30

    nums = re.findall(r"\d+", vel_str.replace(",", ""))
    if nums:
        pct = int(nums[0])
        if pct >= 300:
            return 20
        elif pct >= 100:
            return 10
        else:
            return 5

    if t_type == "RISING":
        return 15

    return 5


def compute_composite_score(
    query: Optional[str] = None,
    trend_type: str = "TOP",
    trend_velocity: str = "Stable",
    serp_audit: Optional[Dict[str, Any]] = None,
    dev_evidence: Optional[Dict[str, Any]] = None,
    keyword: Optional[str] = None,
    serp_score: Optional[int] = None,
    dev_score: Optional[int] = None,
    serp_data: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Computes composite gap score (0 to 100) and maps archetype.
    Enforces hard caps on navigational queries and empty SERPs.
    """
    q = query or keyword or ""
    audit = serp_audit or serp_data or {}
    evidence = dev_evidence or {}

    s_serp = serp_score if serp_score is not None else audit.get("serp_score", 0)
    s_dev = dev_score if dev_score is not None else evidence.get("dev_score", 0)
    s_velocity = calculate_velocity_score(trend_type, trend_velocity)

    raw_sum = s_serp + s_dev + s_velocity
    final_score = min(100, raw_sum)
    archetype, deliverable = classify_archetype(q)

    # Hard Cap 1: Navigational domain queries cannot be high-scoring gaps!
    is_navigational = (
        audit.get("navigational_signal", {}).get("is_navigational", False)
        or kwargs.get("is_navigational", False)
    )
    if is_navigational:
        final_score = min(final_score, 45)  # Hard cap at 45 (Pass/Saturated)
        archetype = "Navigational"
        deliverable = "FALSE POSITIVE — navigational domain search, not an informational gap"

    # Hard Cap 2: Insufficient SERP data (0 results retrieved) = no score
    results_count = audit.get("results_count", None)
    if results_count is not None and results_count == 0:
        final_score = 0
        archetype = "Unaudited"
        deliverable = "Pending SERP verification"

    # Opportunity level classification
    if final_score >= 85:
        tier = "💎 Critical Gold Mine"
    elif final_score >= 65:
        tier = "⚡ High Opportunity"
    else:
        tier = "Pass / Saturated"

    return {
        "keyword": q,
        "gap_score": final_score,
        "serp_score": s_serp,
        "dev_score": s_dev,
        "velocity_score": s_velocity,
        "opportunity_tier": tier,
        "archetype": archetype,
        "deliverable_desc": deliverable,
        "exact_title_matches": audit.get("exact_title_matches"),
        "is_navigational": is_navigational,
        "has_github_issues": evidence.get("has_github_issues", False),
        "has_stack_questions": evidence.get("has_stack_questions", False),
        "top_competitor_title": audit.get("top_competitor_title", ""),
        "top_competitor_url": audit.get("top_competitor_url", ""),
        "breakdown": {
            "serp": s_serp,
            "dev": s_dev,
            "velocity": s_velocity,
        },
    }


# Disguised telemetry alias
evaluate_matrix = compute_composite_score


if __name__ == "__main__":
    # Test navigational query evaluation
    nav_audit = {"serp_score": 0, "results_count": 8, "navigational_signal": {"is_navigational": True}}
    res = compute_composite_score(
        query="calorie calculator net",
        trend_type="TOP",
        trend_velocity="+680%",
        serp_audit=nav_audit,
        dev_score=0,
    )
    print("Navigational Opportunity Score:")
    print(f"Query: {res['keyword']}")
    print(f"Gap Score: {res['gap_score']}/100 (Expected <=45)")
    print(f"Archetype: {res['archetype']} (Expected Navigational)")
    print(f"Tier: {res['opportunity_tier']}")

    # Test Vertical Classifier
    test_queries = [
        "nginx reverse proxy config",
        "heic error windows",
        "affidavit of error sample",
        "calorie calculator net",
        "etsy fee calculator 2026",
    ]
    print("\nVertical Classification Test:")
    for tq in test_queries:
        print(f"'{tq}' -> {classify_vertical(tq)}")
