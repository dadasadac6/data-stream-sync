"""
Multi-Stream Search Suggester & Qualified Intent Harvester (Gold Miner v3.0)
Trio-Stream unblocked search suggestion harvester:
1. DuckDuckGo Autocomplete (Static AC - Uncensored problem-solving queries)
2. Bing OpenSearch JSON (Enterprise, legal, and mature demographic queries)
3. Google Chrome Autocomplete (High-velocity consumer queries)

Applies Qualified Intent Combinatorial Trees to prevent generic head term pollution.
"""

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

from engines.taxonomy_loader import is_intent_rich

logger = logging.getLogger("multi_suggester")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SSL_CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Qualified Intent Combinatorial Modifier Templates
INTENT_MODIFIER_TEMPLATES = [
    # 1. Total Cost & Financial Reality
    "how much does {seed} cost",
    "average cost of {seed}",
    "{seed} pricing guide",
    "cheapest way to {seed}",
    "hidden costs of {seed}",
    
    # 2. Decision Making & Alternatives
    "{seed} alternatives",
    "best {seed} for beginners",
    "is {seed} worth it",
    "{seed} vs",

    # 3. Process, Requirements & Checklists
    "requirements for {seed}",
    "{seed} checklist",
    "documents needed for {seed}",
    "step by step guide to {seed}",

    # 4. Problem-Solving & Disputes
    "how to dispute {seed}",
    "how to cancel {seed}",
    "what to do if {seed} is denied",
]


class MultiStreamSuggester:
    """Trio-stream zero-cost suggestion harvester."""

    def __init__(self):
        self.headers = {"User-Agent": USER_AGENT}

    def fetch_duckduckgo_suggestions(self, query: str) -> List[str]:
        """Harvests uncensored consumer problem suggestions from DuckDuckGo."""
        encoded = urllib.parse.quote(query.strip())
        url = f"https://duckduckgo.com/ac/?q={encoded}&kl=us-en"
        req = urllib.request.Request(url, headers=self.headers)
        results = []

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data:
                    phrase = item.get("phrase", "").strip().lower()
                    if phrase and phrase != query.lower():
                        results.append(phrase)
        except Exception as e:
            logger.debug(f"DuckDuckGo AC error for '{query}': {e}")

        return results

    def fetch_bing_suggestions(self, query: str) -> List[str]:
        """Harvests B2B and mature demographic suggestions from Bing OpenSearch."""
        encoded = urllib.parse.quote(query.strip())
        url = f"http://api.bing.com/osjson.aspx?query={encoded}"
        req = urllib.request.Request(url, headers=self.headers)
        results = []

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) > 1 and isinstance(data[1], list):
                    for phrase in data[1]:
                        p_clean = phrase.strip().lower()
                        if p_clean and p_clean != query.lower():
                            results.append(p_clean)
        except Exception as e:
            logger.debug(f"Bing OpenSearch error for '{query}': {e}")

        return results

    def fetch_google_suggestions(self, query: str) -> List[str]:
        """Harvests Google autocomplete suggestions via Chrome endpoint."""
        encoded = urllib.parse.quote(query.strip())
        url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded}&hl=en"
        req = urllib.request.Request(url, headers=self.headers)
        results = []

        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) > 1 and isinstance(data[1], list):
                    for phrase in data[1]:
                        p_clean = phrase.strip().lower()
                        if p_clean and p_clean != query.lower():
                            results.append(p_clean)
        except Exception as e:
            logger.debug(f"Google AC error for '{query}': {e}")

        return results

    def harvest_trio_stream(self, query: str) -> List[str]:
        """Queries DuckDuckGo, Bing, and Google, merging and deduplicating suggestions."""
        combined = []
        seen = set()

        # Query all three streams
        for stream_fn in [self.fetch_duckduckgo_suggestions, self.fetch_bing_suggestions, self.fetch_google_suggestions]:
            try:
                suggestions = stream_fn(query)
                for s in suggestions:
                    norm = s.strip().lower()
                    if norm not in seen and is_intent_rich(norm):
                        seen.add(norm)
                        combined.append(norm)
            except Exception:
                pass
            time.sleep(0.1)

        return combined

    def expand_seed_with_intent_trees(self, seed: str, max_variations: int = 6) -> List[str]:
        """
        Applies qualified intent combinatorial trees to a seed topic and harvests
        non-generic long-tail suggestions across all three streams.
        """
        all_discovered = []
        seen = set()

        # Pick key intent modifier templates
        selected_templates = INTENT_MODIFIER_TEMPLATES[:max_variations]

        for tmpl in selected_templates:
            targeted_query = tmpl.format(seed=seed)
            suggestions = self.harvest_trio_stream(targeted_query)
            
            for s in suggestions:
                if s not in seen:
                    seen.add(s)
                    all_discovered.append(s)

            time.sleep(0.2)

        logger.info(f"Expanded seed '{seed}' via Intent Trees into {len(all_discovered)} high-intent long-tails")
        return all_discovered


if __name__ == "__main__":
    suggester = MultiStreamSuggester()
    test_seed = "commercial lease letter of intent"
    print(f"Testing Intent Tree Expansion for '{test_seed}':")
    results = suggester.expand_seed_with_intent_trees(test_seed, max_variations=4)
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {r}")
