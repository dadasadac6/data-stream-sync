"""
Universal Root Niche Harvester (Gold Miner)
Harvests broad root terms across 12 evergreen verticals without human hardcoding.
Feeds discovered root anchors into storage/db.py (frontier_niches) with 90-day cooldown enforcement.
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
from typing import Any, Dict, List, Optional
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db

logger = logging.getLogger("niche_ingestor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SSL_CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# 12 Universal Verticals mapping
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

# Baseline high-yield seed anchors per vertical to jumpstart the frontier queue
BASELINE_ROOT_SEEDS: Dict[str, List[str]] = {
    "Finance & Wealth": [
        "mortgage calculator", "loan calculator", "tax calculator", "salary after tax",
        "crypto tax calculator", "compound interest calculator", "car loan payment",
        "dividend calculator", "401k calculator", "roi calculator", "refinance calculator",
        "amortization schedule", "net worth tracker", "capital gains tax calculator",
    ],
    "Small Business & B2B": [
        "invoice generator", "receipt maker", "paystub generator", "nda generator",
        "bill of sale template", "profit margin calculator", "contract template",
        "purchase order template", "business proposal template", "break even calculator",
        "independent contractor agreement", "quote template", "inventory tracker",
    ],
    "Productivity & Work": [
        "budget template", "timesheet template", "habit tracker", "meeting notes template",
        "cron expression generator", "markdown editor", "pomodoro timer", "work breakdown structure",
        "daily planner template", "kanban board template", "flowchart maker", "gantt chart template",
    ],
    "Media & Converters": [
        "heic to jpg", "mp4 to gif", "pdf to word", "compress png",
        "webp to png", "audio extractor", "svg to png", "watermark remover",
        "video compressor", "epub to pdf", "m4a to mp3", "wav to mp3",
        "image resizer", "remove background",
    ],
    "Health & Fitness": [
        "calorie calculator", "macro calculator", "bmi calculator", "running pace calculator",
        "tdee calculator", "water intake calculator", "intermittent fasting tracker",
        "body fat percentage calculator", "one rep max calculator", "ovulation calculator",
        "sleep cycle calculator", "keto diet calculator",
    ],
    "Real Estate & Living": [
        "rent vs buy calculator", "closing cost calculator", "square footage calculator",
        "moving checklist", "lease agreement template", "sublet agreement template",
        "rental yield calculator", "property tax calculator", "roommate agreement template",
        "landlord notice to vacate", "home inspection checklist",
    ],
    "Legal & Compliance": [
        "privacy policy generator", "terms of service generator", "cookie consent banner",
        "power of attorney form", "llc operating agreement template", "non disclosure agreement",
        "cease and desist letter template", "employment contract template", "gdpr checklist",
        "affidavit template", "eviction notice template",
    ],
    "Academic & Education": [
        "gpa calculator", "citation generator", "word counter", "grade calculator",
        "percentage increase calculator", "scientific notation calculator", "weighted grade calculator",
        "plagiarism checker", "flashcard maker", "apa citation maker",
    ],
    "Developer & Cloud": [
        "docker compose template", "fastapi boilerplate", "supabase starter", "jwt refresh token",
        "ollama gpu setup", "kubernetes yaml generator", "sql query builder", "regex tester",
        "nginx reverse proxy config", "tailwind components", "nextjs authentication",
        "cron schedule generator", "rest api documentation template",
    ],
    "Gaming & Entertainment": [
        "damage calculator", "stat calculator", "tier list maker", "wordle solver",
        "mouse sensitivity converter", "crosshair generator", "pokemon weakness chart",
        "fps benchmark calculator", "discord bot template",
    ],
    "E-Commerce & Selling": [
        "etsy fee calculator", "ebay fee calculator", "shopify margin calculator",
        "amazon fba fees calculator", "shipping cost calculator", "barcode generator",
        "drop shipping profit calculator", "product markup calculator", "mercari fee calculator",
    ],
    "Travel & Visas": [
        "schengen 90 180 calculator", "visa requirements for", "flight delay compensation",
        "currency converter", "packing checklist", "passport renewal requirements",
        "jet lag planner", "customs declaration template", "travel budget calculator",
    ],
}


class NicheIngestor:
    """Multi-source root niche harvester populating the frontier queue."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}

    def _queue_term(self, term: str, category: str, parent: Optional[str] = None, depth: int = 0) -> bool:
        """Helper to safely queue term respecting signatures and deduplication."""
        clean = term.strip()
        if not clean or len(clean) < 3:
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

    def ingest_stackoverflow_tags(self, max_pages: int = 3) -> int:
        """Harvests top tags from Stack Exchange API (Developer vertical)."""
        count = 0
        for page in range(1, max_pages + 1):
            url = f"https://api.stackexchange.com/2.3/tags?page={page}&pagesize=100&order=desc&sort=popular&site=stackoverflow"
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                    raw = resp.read()
                    try:
                        content = gzip.decompress(raw).decode("utf-8")
                    except Exception:
                        content = raw.decode("utf-8")
                    data = json.loads(content)
                    items = data.get("items", [])
                    for item in items:
                        tag_name = item.get("name", "").replace("-", " ").strip()
                        if tag_name and len(tag_name) >= 3:
                            # Queue tool variations
                            for suffix in ["", " tutorial", " alternative", " vs"]:
                                term = f"{tag_name}{suffix}".strip()
                                if self._queue_term(term, category="Developer & Cloud", depth=0):
                                    count += 1
                time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                logger.warning(f"Stack Overflow tag ingestion failed on page {page}: {e}")
                break
        logger.info(f"Harvested {count} Developer niche anchors from Stack Overflow tags")
        return count

    def ingest_wikipedia_categories(self) -> int:
        """Traverses Wikipedia categories for calculators, converters, and business tools."""
        category_targets = [
            ("Category:Calculators", "Productivity & Work"),
            ("Category:Financial_software", "Finance & Wealth"),
            ("Category:Unit_converters", "Media & Converters"),
            ("Category:Health_software", "Health & Fitness"),
            ("Category:Legal_software", "Legal & Compliance"),
            ("Category:Educational_software", "Academic & Education"),
        ]
        count = 0
        for cat, vertical in category_targets:
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle={urllib.parse.quote(cat)}&cmlimit=100&format=json"
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    members = data.get("query", {}).get("categorymembers", [])
                    for m in members:
                        title = m.get("title", "")
                        clean = re.sub(r"\(.*?\)", "", title).strip().lower()
                        if clean and len(clean) >= 3 and not clean.startswith("category:"):
                            if self._queue_term(clean, category=vertical, depth=0):
                                count += 1
                time.sleep(random.uniform(0.3, 0.7))
            except Exception as e:
                logger.debug(f"Wikipedia category {cat} fetch error: {e}")
        logger.info(f"Harvested {count} niche anchors from Wikipedia classification tree")
        return count

    def ingest_pypi_popular(self) -> int:
        """Fetches top Python packages for developer utility voids."""
        url = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"
        count = 0
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rows = data.get("rows", [])[:200]
                for r in rows:
                    pkg = r.get("project", "").strip().lower()
                    if pkg and len(pkg) >= 3 and not pkg.startswith("_"):
                        clean = pkg.replace("-", " ").replace("_", " ")
                        if self._queue_term(f"{clean} setup", category="Developer & Cloud", depth=0):
                            count += 1
                        if self._queue_term(f"{clean} alternative", category="Developer & Cloud", depth=0):
                            count += 1
        except Exception as e:
            logger.debug(f"PyPI popular ingest error: {e}")
        logger.info(f"Harvested {count} package seeds from PyPI")
        return count

    def run_all(self) -> Dict[str, int]:
        """Runs the complete multi-source harvester."""
        results = {
            "baseline": self.seed_baseline_taxonomies(),
            "wikipedia": self.ingest_wikipedia_categories(),
            "so_tags": self.ingest_stackoverflow_tags(max_pages=2),
            "pypi": self.ingest_pypi_popular(),
        }
        total = sum(results.values())
        logger.info(f"Total new frontier niches queued across all sources: {total}")
        return results


if __name__ == "__main__":
    ingestor = NicheIngestor()
    stats = ingestor.run_all()
    frontier_stats = db.get_frontier_stats()
    print("\n--- INGESTION COMPLETE ---")
    print(f"Sources yield: {stats}")
    print(f"Frontier Queue Telemetry: Total={frontier_stats['total']}, Pending={frontier_stats['pending']}")
    print(f"Categories Breakdown: {frontier_stats['by_category']}")
