"""
Google Trends Live Trending RSS Harvester (Zero-Cost Stream)
Polls real-time breakout consumer queries across Tier-1 English markets (US, GB, CA, AU, IN).
Filters out ephemeral celebrity and sports noise.
Auto-injects high-intent breakout topics into the frontier queue.
"""

import logging
import os
import re
import ssl
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db
from engines.taxonomy_loader import score_seed_intent, is_intent_rich

logger = logging.getLogger("trends_rss")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SSL_CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Tier-1 Target Markets for Global Traffic
DEFAULT_GEOS = ["US", "GB", "CA", "AU", "IN"]

# Ephemeral Noise Filter (Discard sports matches, pop celebrities, viral gossip)
_NOISE_PATTERNS = re.compile(
    r"\b(fc|vs|match|score|highlights|uefa|nfl|nba|premier league|chelsea|arsenal|"
    r"real madrid|barcelona|cricket|ipl|wwe|ufc|boxing|grammy|oscar|celebrity|"
    r"dating|actress|actor|trailer|episode|album|concert|singer|model)\b",
    re.IGNORECASE,
)

# High-Value Commercial Vertical Intent Keywords
_CATEGORY_KEYWORDS = {
    "Finance & Wealth": ["tax", "bank", "stock", "loan", "mortgage", "fund", "interest", "debt", "insurance", "401k", "crypto", "dividend", "inflation", "recession"],
    "Small Business & B2B": ["business", "contract", "invoice", "freelance", "incorporation", "llc", "trademark", "vendor", "wholesale", "pricing", "sba"],
    "Legal & Compliance": ["court", "lawsuit", "settlement", "decree", "affidavit", "eviction", "attorney", "statute", "lien", "compliance", "regulation", "rights"],
    "Real Estate & Living": ["housing", "mortgage", "rent", "lease", "property", "hoa", "zoning", "inspection", "tenant", "landlord", "appraisal"],
    "Clean Energy & Home": ["solar", "battery", "energy", "heat pump", "generator", "electric", "insulation", "roof", "water heater", "grid"],
    "Health & Fitness": ["diet", "health", "insurance", "fsa", "hsa", "weight", "blood", "medical", "symptom", "vaccine", "exercise", "therapy"],
    "Travel & Visas": ["visa", "passport", "flight", "border", "customs", "travel", "embassy", "tourist", "nomad", "airline"],
    "E-Commerce & Selling": ["amazon", "shopify", "etsy", "ebay", "shipping", "ecommerce", "seller", "tariff", "fba", "delivery"],
}


def classify_trend_category(title: str, snippet: str = "") -> str:
    """Classifies a trending topic into one of the 12 evergreen verticals."""
    text = f"{title} {snippet}".lower()
    for cat, kws in _CATEGORY_KEYWORDS.items():
        for kw in kws:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return cat
    return "Productivity & Work"


class GoogleTrendsRSSHarvester:
    """Ingests live breakout queries with verified search volumes from Google Trends RSS."""

    def __init__(self, geos: Optional[List[str]] = None):
        self.geos = geos or DEFAULT_GEOS

    def fetch_geo_rss(self, geo: str) -> List[Dict[str, Any]]:
        """Fetches and parses Google Trends RSS feed for a specific country."""
        url = f"https://trends.google.com/trending/rss?geo={geo}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        items = []

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                channel = root.find("channel")
                if channel is None:
                    return []

                for item in channel.findall("item"):
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    
                    traffic = ""
                    snippet = ""
                    for child in item:
                        if "approx_traffic" in child.tag:
                            traffic = child.text or ""
                        elif "description" in child.tag:
                            snippet = child.text or ""

                    if title:
                        items.append({
                            "title": title.strip(),
                            "geo": geo,
                            "traffic": traffic.strip(),
                            "pub_date": pub_date,
                            "snippet": snippet.strip(),
                            "link": link
                        })
        except Exception as e:
            logger.warning(f"Error fetching Google Trends RSS for geo={geo}: {e}")

        return items

    def harvest_all_geos(self) -> List[Dict[str, Any]]:
        """Harvests trends across all target geos, deduplicating titles."""
        all_trends = []
        seen_titles = set()

        for geo in self.geos:
            geo_items = self.fetch_geo_rss(geo)
            for item in geo_items:
                norm_title = item["title"].lower().strip()
                if norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    all_trends.append(item)
            time.sleep(0.5)

        logger.info(f"Harvested {len(all_trends)} unique trending items across {len(self.geos)} geos")
        return all_trends

    def filter_and_queue_breakouts(self, trends: List[Dict[str, Any]]) -> int:
        """Filters out ephemeral noise and queues qualified high-intent consumer breakouts."""
        queued_count = 0

        for trend in trends:
            title = trend["title"]
            norm_title = title.lower()

            # 1. Skip obvious ephemeral sports/celebrity noise
            if _NOISE_PATTERNS.search(norm_title):
                continue

            # 2. Categorize
            category = classify_trend_category(title, trend.get("snippet", ""))

            # 3. Queue into frontier_niches
            clean_term = norm_title.strip()
            if is_intent_rich(clean_term):
                if db.queue_sub_niche(clean_term, category=category, depth=0):
                    queued_count += 1
                    logger.info(f"Queued Breakout Trend: '{clean_term}' [{category}] (Traffic: {trend.get('traffic', 'N/A')})")

        return queued_count

    def run(self) -> int:
        """Executes full harvest and enqueue cycle."""
        trends = self.harvest_all_geos()
        count = self.filter_and_queue_breakouts(trends)
        logger.info(f"Successfully processed Google Trends RSS: {count} new breakout topics queued.")
        return count


if __name__ == "__main__":
    harvester = GoogleTrendsRSSHarvester()
    count = harvester.run()
    print(f"Total Breakout Trends Ingested: {count}")
