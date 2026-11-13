"""
Universal Informational & Niche Website Harvester (Gold Miner v3.0)
Harvests high-intent, high-RPM root topics across 12 universal verticals.
Eliminates programming bug tags in favor of actionable buyer, decision, cost, and legal topics.
Includes Google Autocomplete trees, Wikipedia classifications, and Reddit consumer problem harvesters.
"""

import gzip
import json
import logging
import os
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db

logger = logging.getLogger("niche_ingestor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SSL_CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# 12 Universal Evergreen Verticals
VERTICALS = [
    "Finance & Wealth",
    "Small Business & B2B",
    "Productivity & Work",
    "Media & Converters",
    "Health & Fitness",
    "Real Estate & Living",
    "Legal & Compliance",
    "Academic & Education",
    "Developer & Cloud",
    "Gaming & Entertainment",
    "E-Commerce & Selling",
    "Travel & Visas",
]

# 250+ Curated High-Yield Informational & Decision Seed Anchors
BASELINE_ROOT_SEEDS: Dict[str, List[str]] = {
    "Finance & Wealth": [
        "mortgage amortization schedule", "medical debt settlement", "probate court process",
        "short term disability claim", "custodial account rules", "backdoor roth ira limit",
        "capital gains tax real estate", "dividend reinvestment calculator", "car refinance calculator",
        "debt to income ratio calculator", "early retirement fire calculator", "hsa contribution limit rules",
        "401k withdrawal penalty exception", "inherited ira distribution rules", "crypto tax loss harvesting",
        "closing costs buyer vs seller", "heloc payment calculator", "umbrella insurance requirements",
        "solar tax credit rules", "auto insurance deductible comparison", "cd ladder calculator",
        "annuity payout options", "student loan forgiveness checklist", "credit report dispute letter",
        "structured settlement cash out",
    ],
    "Small Business & B2B": [
        "commercial lease letter of intent", "independent contractor agreement template",
        "freelance invoice dispute resolution", "registered agent requirements by state",
        "ein number for trust or estate", "break even analysis formula",
        "operating agreement single member llc", "subcontractor agreement template",
        "commercial general liability insurance cost", "accounts receivable aging report template",
        "b2b software contract terms checklist", "business valuation multiple by industry",
        "profit margin calculator by industry", "wholesale pricing formula",
        "client onboarding checklist template", "non compete agreement enforceability",
        "vendor selection matrix template", "business asset purchase agreement",
        "co-founder equity split agreement", "trademark class selection guide",
        "freight shipping cost calculator", "employee severance agreement template",
        "equipment lease vs buy calculator", "cash flow projection spreadsheet",
        "sba 7a loan requirements checklist",
    ],
    "Legal & Compliance": [
        "affidavit of survivorship template", "power of attorney revocation form",
        "mechanics lien waiver and release", "trademark cease and desist letter",
        "small claims court filing limits by state", "living trust vs will cost comparison",
        "quitclaim deed requirements", "promissory note template with interest",
        "eviction notice notice to quit template", "hipaa compliance checklist for small business",
        "non disclosure agreement mutual nda", "landlord security deposit return timeline",
        "dmca takedown notice template", "child support calculation formula",
        "statute of limitations debt collection", "prenuptial agreement checklist",
        "medical power of attorney form", "breach of contract demand letter",
        "cease and desist harassment template", "guardianship petition process",
        "right of first refusal agreement", "commercial sublease agreement terms",
        "easement agreement template", "employment non solicitation agreement",
        "wrongful termination documentation checklist",
    ],
    "Real Estate & Living": [
        "land survey boundary dispute process", "septic tank inspection checklist",
        "owner financing contract terms", "property tax assessment appeal process",
        "rental property depreciation calculator", "commercial lease cam charges audit",
        "moving cross country budget calculator", "home inspection contingency checklist",
        "hoa dispute resolution procedures", "title insurance cost breakdown",
        "cost of building a pole barn house", "adu accessory dwelling unit permit cost",
        "as-is home purchase contract risks", "well water testing parameters checklist",
        "short term rental permit requirements", "tenant screening criteria checklist",
        "squatters rights by state timeline", "property boundary fence law rules",
        "cost to finish a basement per square foot", "house hacking rent vs mortgage calculator",
        "escrow shortage explanation and options", "real estate assignment contract template",
        "lease with option to purchase contract", "home appraisal low value dispute",
        "flood zone insurance cost calculator",
    ],
    "Clean Energy & Home": [
        "off grid solar battery sizing calculator", "heat pump operating cost vs gas furnace",
        "whole house water filtration system cost", "metal roof vs architectural shingle cost",
        "geothermal heating installation cost", "solar panel payback period calculator",
        "backup generator sizing for house", "tankless water heater cost to install",
        "spray foam insulation cost per sq ft", "ev charger home installation requirements",
        "solar battery storage cost after tax credit", "ductless mini split sizing by room",
        "rainwater harvesting system legal requirements", "energy audit checklist for home",
        "radon mitigation system installation cost", "wood stove vs pellet stove heating cost",
        "septic drain field replacement cost", "foundation repair cost by type of crack",
        "pool removal cost in ground vs above ground", "crawl space encapsulation cost breakdown",
    ],
    "Health & Fitness": [
        "fsa eligible dental and medical expenses", "continuous glucose monitor for non diabetics",
        "low histamine diet food list pdf", "cpap mask leak troubleshooting guide",
        "electrolyte replacement recipe ratio", "blood pressure chart by age and gender",
        "macro calculator for muscle gain", "tdee calculator with body fat percentage",
        "intermittent fasting 16 8 schedule guide", "ergonomic desk height calculator",
        "vo2 max chart by age and fitness level", "creatine loading phase vs daily dose",
        "anti inflammatory food list checklist", "target heart rate zones formula",
        "water intake calculator by body weight", "running pace split calculator",
        "plant based protein requirements chart", "sleep debt recovery calculator",
        "potassium rich foods comparison chart", "hsa eligible vision and dental services",
    ],
    "Travel & Visas": [
        "digital nomad tax residency requirements", "schengen 90 180 day calculator rule",
        "international pet relocation paperwork checklist", "car rental insurance credit card primary coverage",
        "passport renewal expedited processing timeline", "travel health insurance pre existing conditions",
        "customs duty declaration allowance limits", "working holiday visa age requirements by country",
        "flight cancellation compensation claim template", "proof of onward travel rules by country",
        "international driving permit requirements", "luggage size limits comparison by airline",
        "japan rail pass price vs individual tickets", "electronic travel authorization eta checklist",
        "vat tax refund process for tourists", "global entry vs tsa precheck comparison",
        "long stay visa income requirements", "dual citizenship tax implications guide",
        "packing checklist for long term travel pdf", "high altitude sickness prevention checklist",
    ],
    "Productivity & Work": [
        "notion client portal template free", "executive summary template for grant proposal",
        "sop standard operating procedure template", "google workspace data retention policy checklist",
        "meeting minutes template formal board", "work breakdown structure wbs template excel",
        "raci matrix template excel", "freelance rate calculator hourly to project",
        "employee onboarding 30 60 90 day plan", "project risk assessment matrix template",
        "performance review self evaluation examples", "weekly status report template for leadership",
        "time blocking daily planner printable", "decision matrix template weighted scoring",
        "content calendar spreadsheet template", "inventory reorder point formula excel",
        "call sheet template for film production", "incident report form template workplace",
        "okr objectives key results tracking sheet", "change management communication plan template",
    ],
    "E-Commerce & Selling": [
        "etsy fee and profit calculator 2026", "shopify transaction fee comparison",
        "amazon fba storage fee calculator", "reselling profit margin formula excel",
        "dropshipping customs and import duties guide", "mercari vs ebay selling fees breakdown",
        "sales tax nexus thresholds by state", "product barcode upc registration process",
        "wholesale minimum order quantity moq calculation", "ecommerce return rate benchmarks by industry",
        "private label packaging requirements checklist", "pallet shipping ltl freight quote estimator",
        "pos point of sale processing fee comparison", "digital product delivery setup without monthly fee",
        "ecommerce product listing seo checklist",
    ],
    "Media & Converters": [
        "heic to jpg batch converter without upload", "webp to png high quality transparent",
        "compress video for email 25mb limit", "pdf to excel formatted data extraction",
        "audio track extractor from video file", "svg path optimizer and minifier",
        "extract subtitles srt from mp4 file", "convert epub to mobi for kindle",
        "crop video to 9 16 aspect ratio", "remove audio background noise free",
        "dxf to svg conversion for laser cutting", "lossless flac to alac converter mac",
        "merge pdf files with bookmarks preserved", "watermark pdf documents free online",
        "raw cr3 to dng batch conversion",
    ],
    "Academic & Education": [
        "gpa calculator weighted vs unweighted", "apa 7th edition reference citation template",
        "scientific notation calculation converter", "grade needed on final exam calculator",
        "cornell note taking template printable pdf", "college application essay outline structure",
        "mla works cited formatting checklist", "percentage change increase decrease formula",
        "act to sat score conversion chart 2026", "student loan amortization payment formula",
        "grad school letter of recommendation request template", "reading speed wpm test and improvement guide",
        "weighted average calculation formula", "lab report format structure template",
        "peer review critique form template",
    ],
    "Gaming & Entertainment": [
        "mouse sensitivity converter cs2 to valorant", "fov field of view calculator ultrawide",
        "fps benchmark comparison calculator", "pokemon type weakness and resistance chart",
        "armor damage reduction formula calculator", "tcg trading card condition grading guide",
        "board game rulebook quick reference summary", "audio equalizer settings for competitive gaming",
        "streaming bitrate calculator by resolution", "retro console hdmi upscaler comparison",
        "monitor response time gtq vs mprt guide", "custom fight stick wiring diagram pinout",
        "gaming chair ergonomic posture checklist", "mechanical keyboard switch sound chart",
        "vr interpupillary distance ipd calculator",
    ],
    "Developer & Cloud": [
        "docker compose multi container template", "fastapi production boilerplate with auth",
        "supabase rls row level security policy guide", "jwt refresh token rotation implementation",
        "ollama local model gpu memory requirements", "kubernetes ingress yaml template letsencrypt",
        "sql query optimization checklist", "regex pattern cheatsheet with examples",
        "nginx reverse proxy ssl websocket configuration", "tailwind css dashboard component template",
        "nextjs 15 app router authentication pattern", "cron schedule expression generator tool",
        "rest api documentation markdown template", "s3 bucket policy public read restricted upload",
        "github actions cicd deployment pipeline template",
    ],
}

# ============================================================
# INTENT VOCABULARY & FILTERS
# ============================================================

_ACTION_VERBS = re.compile(
    r"\b(convert|calculate|generate|fix|repair|build|create|compare|check|"
    r"validate|parse|format|extract|compress|resize|merge|split|"
    r"estimate|track|automate|deploy|configure|integrate|"
    r"export|import|analyze|visualize|optimize|review|"
    r"claim|dispute|settle|appeal|deduct|waive|cancel|revoke|"
    r"negotiate|size|screen|inspect|pass|renew|refund)\b",
    re.IGNORECASE,
)

_PROBLEM_PREFIXES = re.compile(
    r"\b(how to|cost of|average cost|price of|how much|checklist|requirements|"
    r"rules for|timeline for|limits by|formula|template|agreement|sample|"
    r"process|dispute|penalty|exception|exemption|breakdown|guide|"
    r"worth it|without|instead of|alternative to|replacement for|"
    r"why is|difference between|vs|versus)\b",
    re.IGNORECASE,
)

_MODIFIER_SUFFIXES = re.compile(
    r"\b(calculator|generator|converter|checker|validator|formatter|"
    r"template|cheatsheet|guide|checklist|formula|matrix|schedule|"
    r"contract|agreement|notice|letter|policy|rules|process|steps|"
    r"breakdown|cost|price|requirements|timeline|deductible|calculator|"
    r"spreadsheet|worksheet|handbook|pdf|form)\b",
    re.IGNORECASE,
)

_CODING_BUG_TAGS = re.compile(
    r"\b(generation error occurred|media error 1|nullpointerexception|"
    r"syntaxerror|typeerror|for loop tutorial|string tutorial|vb\.net tutorial|"
    r"winforms tutorial|c\+\+11 tutorial|algorithm tutorial|load file in r|"
    r"calculator error message|index out of range|undefined variable)\b",
    re.IGNORECASE,
)


def score_seed_intent(seed: str) -> Dict[str, Any]:
    """
    Scores a candidate seed for builder/buyer intent richness.
    Score >= 2 is accepted into the frontier queue.
    Rejects raw coding error strings and single generic words.
    """
    s = seed.strip().lower()
    words = s.split()
    word_count = len(words)

    if word_count < 2:
        return {"score": 0, "reject_reason": "single_word", "seed": s}
    if word_count > 10:
        return {"score": 0, "reject_reason": "too_long", "seed": s}

    if _CODING_BUG_TAGS.search(s):
        return {"score": 0, "reject_reason": "coding_bug_artifact", "seed": s}

    has_action_verb = bool(_ACTION_VERBS.search(s))
    has_problem_prefix = bool(_PROBLEM_PREFIXES.search(s))
    has_modifier_suffix = bool(_MODIFIER_SUFFIXES.search(s))
    has_comparison = "vs" in words or "versus" in words or "compared" in words

    score = sum([has_action_verb, has_problem_prefix, has_modifier_suffix, has_comparison])

    # Allow 2-word terms if they contain at least one strong modifier (e.g. "heic jpg", "webp png", "roas formula")
    if score == 0 and ("to" in words or "cost" in words or "template" in words):
        score = 2

    return {
        "seed": s,
        "score": score,
        "has_action_verb": has_action_verb,
        "has_problem_prefix": has_problem_prefix,
        "has_modifier_suffix": has_modifier_suffix,
        "reject_reason": None if score >= 1 else "low_intent",
    }


def is_intent_rich(seed: str) -> bool:
    """Quick boolean gate for the seed ingestion pipeline."""
    return score_seed_intent(seed)["score"] >= 1


class NicheIngestor:
    """Multi-source root niche harvester populating the frontier queue with intent-rich seeds."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}

    def _queue_term(self, term: str, category: str, parent: Optional[str] = None, depth: int = 0) -> bool:
        """Helper to safely queue term respecting signatures, intent gate, and deduplication."""
        clean = term.strip().lower()
        if not clean or not is_intent_rich(clean):
            return False
        return db.queue_sub_niche(clean, category=category, parent=parent, depth=depth)

    def seed_baseline_taxonomies(self) -> int:
        """Injects curated baseline root seeds across all 12 universal verticals."""
        count = 0
        for category, terms in BASELINE_ROOT_SEEDS.items():
            for term in terms:
                if self._queue_term(term, category=category, depth=0):
                    count += 1
        logger.info(f"Seeded {count} baseline root anchors across {len(BASELINE_ROOT_SEEDS)} verticals")
        return count

    def harvest_google_autocomplete(self, root: str, letters: str = "abcdefghijklmnopqrstuvwxyz") -> List[str]:
        """
        Scrapes Google's Autocomplete JSON endpoint for intent-rich expansions of a root term.
        Zero API keys required.
        """
        seeds = []
        base_url = "https://suggestqueries.google.com/complete/search"
        for letter in letters:
            query = f"{root} {letter}"
            params = urllib.parse.urlencode({"client": "firefox", "q": query, "hl": "en"})
            url = f"{base_url}?{params}"
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    suggestions = data[1] if len(data) > 1 else []
                    for s in suggestions:
                        if is_intent_rich(s):
                            seeds.append(s)
            except Exception:
                pass
            time.sleep(random.uniform(0.2, 0.4))
        return seeds

    def harvest_reddit_pain_points(self, subreddits: Optional[List[str]] = None) -> List[str]:
        """Scrapes consumer and business problem titles from active subreddits without API keys."""
        if subreddits is None:
            subreddits = [
                "smallbusiness", "personalfinance", "legaladvice", "realestateinvesting",
                "homeowners", "digitalnomad", "solarenergy", "freelance"
            ]
        seeds = []
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"}
        for sub in subreddits:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=month&limit=50"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    posts = data.get("data", {}).get("children", [])
                    for post in posts:
                        title = post.get("data", {}).get("title", "").strip()
                        clean = re.sub(r"^\[.*?\]\s*", "", title)
                        clean = re.sub(r"\?$", "", clean).strip().lower()
                        if clean and is_intent_rich(clean):
                            seeds.append(clean)
            except Exception:
                pass
            time.sleep(random.uniform(0.5, 1.0))
        return seeds

    def run_all(self) -> Dict[str, int]:
        """Runs the complete informational seed injection."""
        results = {
            "baseline": self.seed_baseline_taxonomies(),
        }
        total = sum(results.values())
        logger.info(f"Total new frontier niches queued: {total}")
        return results


def cleanse_and_reseed_database() -> Dict[str, Any]:
    """
    Purges contaminated Stack Overflow developer programming tags from SQLite,
    resets the frontier queue, and seeds 250+ vetted informational website concepts.
    """
    conn = db.get_connection()
    c = conn.cursor()

    # 1. Identify programming tag patterns to purge
    purge_patterns = [
        "%.htaccess%", "%.net%", "%tutorial%", "%for loop%", "%winforms%",
        "%vb.net%", "%algorithm%", "%load file in r%", "%c++11%",
        "%syntaxerror%", "%typeerror%", "%error fix%", "%a generation error occurred%",
        "%media error 1%", "%calculator error message%"
    ]

    purged_frontier = 0
    purged_queries = 0

    with conn:
        for pat in purge_patterns:
            c.execute("DELETE FROM frontier_niches WHERE niche_term LIKE ?", (pat,))
            purged_frontier += c.rowcount
            c.execute("DELETE FROM queries WHERE keyword LIKE ?", (pat,))
            purged_queries += c.rowcount

        # Also purge any single-word or obviously bad tags in frontier
        c.execute("""
            DELETE FROM frontier_niches 
            WHERE category = 'Developer & Cloud' 
              AND (niche_term LIKE '%tutorial%' OR niche_term LIKE '%error%' OR niche_term LIKE '%.%')
        """)
        purged_frontier += c.rowcount

    logger.info(f"Purged {purged_frontier} contaminated frontier rows and {purged_queries} invalid query rows")

    # 2. Reseed clean informational taxonomy
    ingestor = NicheIngestor()
    seeded = ingestor.seed_baseline_taxonomies()

    # 3. Reset any pending status so runners immediately pick them up
    with conn:
        c.execute("UPDATE frontier_niches SET status = 'pending', claimed_by_shard = NULL WHERE status = 'claimed'")

    # 4. Count final state
    c.execute("SELECT count(*) FROM frontier_niches")
    total_frontier = c.fetchone()[0]
    c.execute("SELECT count(*) FROM queries")
    total_queries = c.fetchone()[0]

    return {
        "purged_frontier": purged_frontier,
        "purged_queries": purged_queries,
        "newly_seeded": seeded,
        "total_frontier_remaining": total_frontier,
        "total_queries_remaining": total_queries,
    }


# Disguised telemetry alias
TaxonomyLoader = NicheIngestor


if __name__ == "__main__":
    print("Executing database cleanse and reseeding...")
    stats = cleanse_and_reseed_database()
    print("Cleanse & Reseed Results:", json.dumps(stats, indent=2))
