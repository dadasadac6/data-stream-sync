"""
Mathematical Scoring & Archetype Classification Engine
Calculates the 0-100 Composite Opportunity Score based on:
  Final Gap Score = S_SERP (0-40) + S_Dev (0-30) + S_Velocity (0-30)
Maps qualified opportunities into 4 Developable Archetypes:
  1. Micro-Tool
  2. Workaround
  3. Recipe
  4. Breaking News
"""

import re
from typing import Any, Dict, Tuple

# Archetype keyword trigger mappings
ARCHETYPE_RULES = [
    {
        "archetype": "Micro-Tool",
        "description": "Single-page responsive web utility, calculator, or formatter with programmatic SEO",
        "keywords": [
            "calculator", "converter", "generator", "viewer", "validator",
            "formatter", "tester", "playground", "diff", "visualizer",
            "parser", "decoder", "encoder", "builder", "checker", "linter",
            "mock", "sandbox", "minifier", "beautifier", "editor", "tool"
        ],
    },
    {
        "archetype": "Workaround",
        "description": "Definitive troubleshooting guide with verified code snippets and patch scripts",
        "keywords": [
            "how to fix", "error", "failed to", "cannot resolve", "loop",
            "bypass", "patch", "mismatch", "unexpected", "crash",
            "timeout", "connection refused", "out of memory", "killed",
            "not working", "unable to", "issue", "bug", "exception",
            "unhandled", "denied", "forbidden", "broken", "hangs"
        ],
    },
    {
        "archetype": "Breaking News",
        "description": "Rapid technical migration brief, changelog breakdown, or compatibility guide",
        "keywords": [
            "release date", "what is new", "breaking changes", "migration from",
            "deprecation", "roadmap", "benchmark", "announcement", "v2",
            "v3", "v4", "v5", "2026", "2025", "changelog", "update"
        ],
    },
    {
        "archetype": "Recipe",
        "description": "GitHub starter repository, 1-click template, or copy-paste reference cheatsheet",
        "keywords": [
            "boilerplate", "starter", "template", "cheatsheet", "best practices",
            "docker compose for", "config for", "example", "setup",
            "integration", "tutorial", "reference", "guide", "pattern",
            "architecture", "scaffold", "stack", "quickstart", "how to use"
        ],
    },
]


def classify_archetype(query: str) -> Tuple[str, str]:
    """
    Classifies a search query into one of the 4 Developable Archetypes.
    Returns (archetype_name, deliverable_description).
    """
    q_lower = query.lower()

    for rule in ARCHETYPE_RULES:
        for kw in rule["keywords"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower) or kw in q_lower:
                return rule["archetype"], rule["description"]

    # Fallback heuristic: If query starts with "how to", default to Workaround or Recipe
    if q_lower.startswith("how to") or "fix" in q_lower:
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

    # Extract numerical percentage if available (e.g., "+3,200%")
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
    query: str,
    trend_type: str,
    trend_velocity: str,
    serp_audit: Dict[str, Any],
    dev_evidence: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes composite gap score (0 to 100) and maps archetype.
    """
    s_serp = serp_audit.get("serp_score", 0)  # Max 40
    s_dev = dev_evidence.get("dev_score", 0)   # Max 30
    s_velocity = calculate_velocity_score(trend_type, trend_velocity)  # Max 30

    final_score = min(100, s_serp + s_dev + s_velocity)
    archetype, deliverable = classify_archetype(query)

    # Opportunity level classification
    if final_score >= 85:
        tier = "💎 Critical Gold Mine"
    elif final_score >= 65:
        tier = "⚡ High Opportunity"
    else:
        tier = "Pass / Saturated"

    return {
        "keyword": query,
        "gap_score": final_score,
        "serp_score": s_serp,
        "dev_score": s_dev,
        "velocity_score": s_velocity,
        "opportunity_tier": tier,
        "archetype": archetype,
        "deliverable_desc": deliverable,
        "exact_title_matches": serp_audit.get("exact_title_matches", 0),
        "has_github_issues": dev_evidence.get("has_github_issues", False),
        "has_stack_questions": dev_evidence.get("has_stack_questions", False),
        "top_competitor_title": serp_audit.get("top_competitor_title", ""),
        "top_competitor_url": serp_audit.get("top_competitor_url", ""),
    }


if __name__ == "__main__":
    sample_serp = {"serp_score": 35, "exact_title_matches": 0, "top_competitor_title": "Forum post", "top_competitor_url": "https://reddit.com"}
    sample_dev = {"dev_score": 25, "has_github_issues": True, "has_stack_questions": True}
    res = compute_composite_score(
        query="fastapi jwt refresh token boilerplate",
        trend_type="BREAKOUT",
        trend_velocity="Breakout",
        serp_audit=sample_serp,
        dev_evidence=sample_dev,
    )
    print("Scoring Result:")
    for k, v in res.items():
        print(f"  {k}: {v}")
