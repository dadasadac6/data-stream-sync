"""
Semantic Silo Clustering & Website Doability Engine (Data Stream Sync v3.0)
Groups harvested queries into coherent Topical Website Silos (Pillars + Clusters).
Calculates the Proprietary 4-Factor Website Doability Index (0-100).
Synthesizes 1-Click Production Blueprints (Domains, Pillar, Clusters, Lead Magnet, Monetization).
Zero cloud dependencies: pure fast Python + n-gram vector graph partitioning.
"""

import collections
import math
import os
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db

# Vertical RPM Multipliers (Based on Mediavine / Raptive / Affiliate benchmarks)
RPM_TIERS = {
    "Finance & Wealth": {"score": 100, "label": "High ($55 - $125 RPM)", "bounty": "$75 - $150 / lead"},
    "Legal & Compliance": {"score": 100, "label": "High ($65 - $150 RPM)", "bounty": "$60 - $120 / sale"},
    "Small Business & B2B": {"score": 95, "label": "High ($50 - $110 RPM)", "bounty": "$50 - $100 / lead"},
    "Clean Energy & Home": {"score": 90, "label": "High ($40 - $95 RPM)", "bounty": "$40 - $85 / quote"},
    "Real Estate & Living": {"score": 85, "label": "Medium-High ($35 - $80 RPM)", "bounty": "$30 - $70 / lead"},
    "Health & Fitness": {"score": 75, "label": "Medium ($25 - $60 RPM)", "bounty": "$20 - $50 / order"},
    "Travel & Visas": {"score": 70, "label": "Medium ($25 - $55 RPM)", "bounty": "$15 - $45 / booking"},
    "E-Commerce & Selling": {"score": 65, "label": "Medium ($20 - $50 RPM)", "bounty": "$15 - $40 / signup"},
    "Productivity & Work": {"score": 60, "label": "Medium ($20 - $45 RPM)", "bounty": "$10 - $35 / sale"},
    "Media & Converters": {"score": 45, "label": "Low-Medium ($12 - $30 RPM)", "bounty": "$5 - $20 / sub"},
    "Academic & Education": {"score": 40, "label": "Low-Medium ($10 - $25 RPM)", "bounty": "$5 - $15 / user"},
    "Gaming & Entertainment": {"score": 30, "label": "Low ($6 - $18 RPM)", "bounty": "$2 - $10 / install"},
    "Developer & Cloud": {"score": 50, "label": "Medium ($18 - $40 RPM)", "bounty": "$15 - $40 / tier"},
}

# Stopwords for clean semantic grouping
_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "how", "what", "which", "who", "when", "where", "why", "can", "will", "would",
}


def tokenize_query(query: str) -> List[str]:
    """Tokenizes and cleans search terms into informative words."""
    words = re.findall(r"\b[a-z0-9]{2,}\b", query.lower())
    return [w for w in words if w not in _STOPWORDS]


def compute_token_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Computes Jaccard-Dice hybrid similarity between token lists."""
    if not tokens_a or not tokens_b:
        return 0.0
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    intersection = len(set_a & set_b)
    if intersection == 0:
        return 0.0
    return (2.0 * intersection) / (len(set_a) + len(set_b))


class TopicClusterEngine:
    """Clusters database queries into cohesive website topical silos."""

    def __init__(self, similarity_threshold: float = 0.38):
        self.threshold = similarity_threshold

    def cluster_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups list of query items into clusters."""
        if not items:
            return []

        # Tokenize all
        token_map = {idx: tokenize_query(item.get("keyword", "")) for idx, item in enumerate(items)}
        visited = set()
        clusters = []

        # Sort by gap_score descending so high-value opportunities become cluster anchors
        sorted_indices = sorted(range(len(items)), key=lambda i: items[i].get("gap_score", 0), reverse=True)

        for i in sorted_indices:
            if i in visited:
                continue

            visited.add(i)
            root_item = items[i]
            t1 = token_map[i]
            cluster_members = [root_item]

            for j in sorted_indices:
                if j not in visited:
                    # Same category boost
                    if items[j].get("category") == root_item.get("category"):
                        sim = compute_token_similarity(t1, token_map[j])
                        if sim >= self.threshold:
                            visited.add(j)
                            cluster_members.append(items[j])

            # Build cluster representation
            cluster_data = self._build_silo_data(cluster_members)
            clusters.append(cluster_data)

        # Sort clusters by Doability Score descending
        clusters.sort(key=lambda c: c["doability_score"], reverse=True)
        return clusters

    def _build_silo_data(self, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates Doability Index and synthesizes the website silo blueprint."""
        pillar = members[0]
        category = pillar.get("category", "General")
        cluster_size = len(members)

        # 1. SERP Vulnerability Component (0-100, 35% weight)
        exact_titles = min((m.get("exact_title_matches") if m.get("exact_title_matches") is not None else 0) for m in members)
        if exact_titles == 0:
            v_serp = 100
            serp_status = "0/10 Untouched Void"
        elif exact_titles <= 2:
            v_serp = 75
            serp_status = f"{exact_titles}/10 Low Competition"
        else:
            v_serp = 35
            serp_status = f"{exact_titles}/10 Competed"

        # Forum displacement bonus (Reddit/Quora ranking)
        has_forum = any("reddit" in (m.get("top_competitor_url") or "").lower() or "quora" in (m.get("top_competitor_url") or "").lower() for m in members)
        if has_forum and v_serp < 95:
            v_serp = 95
            serp_status = "UGC / Forum Dominated (#1-#3 Reddit/Quora)"

        # 2. Silo Depth Component (0-100, 25% weight)
        d_silo = min(100.0, (cluster_size / 6.0) * 100.0)

        # 3. Monetization RPM Component (0-100, 20% weight)
        rpm_info = RPM_TIERS.get(category, {"score": 50, "label": "Standard", "bounty": "Standard"})
        m_rpm = rpm_info["score"]

        # 4. Search Momentum Component (0-100, 20% weight)
        is_breakout = any(m.get("trend_type") == "BREAKOUT" for m in members)
        t_velocity = 100 if is_breakout else 70

        # Composite Doability Score (0-100)
        doability_score = int(round(
            (0.35 * v_serp) + (0.25 * d_silo) + (0.20 * m_rpm) + (0.20 * t_velocity)
        ))

        # Generate Website Blueprint
        blueprint = self._generate_blueprint(pillar["keyword"], category, members, rpm_info)

        return {
            "pillar_keyword": pillar["keyword"],
            "category": category,
            "cluster_size": cluster_size,
            "doability_score": doability_score,
            "v_serp": v_serp,
            "serp_status": serp_status,
            "rpm_label": rpm_info["label"],
            "lead_bounty": rpm_info["bounty"],
            "pillar_gap_score": pillar.get("gap_score", 0),
            "trend_velocity": pillar.get("trend_velocity", "Stable"),
            "members": members,
            "blueprint": blueprint,
        }

    def _generate_blueprint(self, pillar_kw: str, category: str, members: List[Dict[str, Any]], rpm_info: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes actionable domain, articles, and lead assets for the cluster."""
        clean_words = [w for w in re.findall(r"\b[a-z0-9]+\b", pillar_kw.lower()) if w not in _STOPWORDS][:3]
        base_slug = "".join(w.capitalize() for w in clean_words)

        domains = [
            f"{base_slug}HQ.com",
            f"{base_slug}Guide.com",
            f"The{base_slug}Hub.com",
        ]

        # Supporting articles
        cluster_articles = []
        for m in members[1:6]:
            kw = m.get("keyword", "")
            cluster_articles.append({
                "target_query": kw,
                "title": f"The Complete Guide to {kw.title()}: Steps, Costs & Rules",
                "format": "In-Depth Cluster Guide"
            })

        # Lead Magnet / Interactive asset
        interactive_asset = f"1-Page Interactive {pillar_kw.title()} Calculator & Decision Worksheet"
        if "template" in pillar_kw or "agreement" in pillar_kw or "affidavit" in pillar_kw:
            interactive_asset = f"Downloadable {pillar_kw.title()} Template (Word / PDF) + Clause Checklist"
        elif "checklist" in pillar_kw or "requirements" in pillar_kw:
            interactive_asset = f"Printable {pillar_kw.title()} Step-by-Step Compliance Checklist"

        return {
            "suggested_domains": domains,
            "pillar_page": {
                "title": f"The Master Guide to {pillar_kw.title()} (2026 Edition)",
                "target_query": pillar_kw,
                "target_words": 2500,
                "core_sections": [
                    f"Understanding {pillar_kw.title()}: Core Definitions & Scope",
                    "Cost Breakdown, Hidden Fees & Price Ranges",
                    "Step-by-Step Execution Process & Statutory Timelines",
                    "Common Mistakes & Expensive Pitfalls to Avoid",
                    "Frequently Asked Questions & Expert Tips"
                ]
            },
            "cluster_articles": cluster_articles,
            "interactive_asset": interactive_asset,
            "monetization": {
                "display_rpm": rpm_info["label"],
                "affiliate_bounty": rpm_info["bounty"],
                "primary_model": "High-Ticket Lead Generation & Affiliate Templates"
            }
        }


def get_doable_website_ideas(limit: int = 50, min_score: int = 60) -> List[Dict[str, Any]]:
    """Fetches queries from DB, clusters them, and returns top doable website ideas."""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT keyword, category, trend_type, trend_velocity, gap_score, archetype, 
               exact_title_matches, top_competitor_title, top_competitor_url 
        FROM queries 
        ORDER BY gap_score DESC 
        LIMIT 1000
    """)
    rows = [dict(r) for r in c.fetchall()]

    engine = TopicClusterEngine()
    clusters = engine.cluster_items(rows)
    
    # Filter by minimum doability score
    qualified = [c for c in clusters if c["doability_score"] >= min_score]
    return qualified[:limit]


if __name__ == "__main__":
    print("Testing Topic Clustering & Doability Engine on existing DB queries...")
    ideas = get_doable_website_ideas(limit=10, min_score=50)
    print(f"\nDiscovered {len(ideas)} Highly Doable Website Ideas:\n")
    for idx, idea in enumerate(ideas, 1):
        print(f"{idx}. [{idea['doability_score']}/100] {idea['pillar_keyword'].upper()}")
        print(f"   Category: {idea['category']} | Cluster Size: {idea['cluster_size']} | SERP: {idea['serp_status']}")
        print(f"   RPM: {idea['rpm_label']} | Suggested Domain: {idea['blueprint']['suggested_domains'][0]}")
        print(f"   Lead Asset: {idea['blueprint']['interactive_asset']}")
        if idea['blueprint']['cluster_articles']:
            print(f"   Sub-Articles: {len(idea['blueprint']['cluster_articles'])} cluster guides")
        print()
