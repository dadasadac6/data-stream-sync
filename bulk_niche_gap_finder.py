#!/usr/bin/env python3
"""
Bulk Free Search Gap & Niche Opportunity Finder
- 100% Free, No API Keys Required
- Uses Google Suggest for demand verification
- Uses DuckDuckGo SERP parser for competition & forum weak-spot analysis
- Exports sorted opportunities to CSV with resume/checkpoint support
"""

import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from html import unescape

# Weak competition platforms that indicate a content gap when ranking high
WEAK_DOMAINS = [
    "reddit.com", "quora.com", "medium.com", "pinterest.com",
    "linkedin.com/pulse", "tripadvisor.com", "discussions.apple.com",
    "stackoverflow.com", "answers.yahoo.com", "forum", "community"
]

CTX = ssl._create_unverified_context()
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

def check_google_suggest(keyword):
    """Checks if Google suggests this keyword or related variations (validates demand)."""
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(keyword)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            suggestions = data[1] if len(data) > 1 else []
            return len(suggestions) > 0, suggestions[:3]
    except Exception:
        return False, []

def fetch_serp_results(keyword):
    """Fetches top organic results via free HTML endpoint."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return []

    blocks = re.findall(r'<div class="result results_links.*?\">(.*?)</div>\s*</div>', html, re.DOTALL)
    results = []

    for b in blocks[:10]:
        m_url = re.search(r'uddg=([^&]+)', b)
        m_title = re.search(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', b, re.DOTALL)
        if m_url and m_title:
            real_url = urllib.parse.unquote(m_url.group(1))
            clean_title = unescape(re.sub(r'<[^>]+>', '', m_title.group(1))).strip()
            results.append({"title": clean_title, "url": real_url})

    return results

def evaluate_keyword_gap(keyword):
    """Calculates a Gap Opportunity Score (0 to 100)."""
    has_demand, top_suggests = check_google_suggest(keyword)
    serp = fetch_serp_results(keyword)

    if not serp:
        return None

    kw_lower = keyword.lower().strip()
    forum_count = 0
    top_forum_rank = None
    exact_title_count = 0

    for idx, item in enumerate(serp):
        rank = idx + 1
        url_lower = item["url"].lower()
        title_lower = item["title"].lower()

        # Check exact title match
        if kw_lower in title_lower:
            exact_title_count += 1

        # Check forum / weak site
        is_weak = any(w in url_lower for w in WEAK_DOMAINS)
        if is_weak:
            forum_count += 1
            if top_forum_rank is None:
                top_forum_rank = rank

    # Calculate Opportunity Score:
    # High score = High gap / low competition
    score = 0

    # 1. Forum signals (up to 45 pts)
    if top_forum_rank == 1:
        score += 45
    elif top_forum_rank in (2, 3):
        score += 35
    elif top_forum_rank and top_forum_rank <= 5:
        score += 25
    elif forum_count >= 1:
        score += 15

    # 2. Competitor title optimization (up to 35 pts)
    if exact_title_count == 0:
        score += 35  # Nobody targeted this exact phrase in title!
    elif exact_title_count == 1:
        score += 25
    elif exact_title_count <= 3:
        score += 15

    # 3. Validated search demand (up to 20 pts)
    if has_demand:
        score += 20

    # Opportunity category
    if score >= 70:
        category = "🔥 GOLDEN GAP (Easy to Rank)"
    elif score >= 45:
        category = "⚡ MODERATE GAP"
    else:
        category = "❌ HIGH COMPETITION"

    return {
        "keyword": keyword,
        "score": score,
        "opportunity": category,
        "exact_title_matches": exact_title_count,
        "forums_in_top10": forum_count,
        "top_forum_rank": top_forum_rank or "None",
        "has_search_demand": "Yes" if has_demand else "Low/None",
        "top_ranking_title": serp[0]["title"] if serp else "",
        "top_ranking_url": serp[0]["url"] if serp else ""
    }

def run_bulk_gap_analysis(input_file="keywords.txt", output_file="niche_gaps.csv", delay=0.8):
    if not os.path.exists(input_file):
        print(f"File '{input_file}' not found. Please create it with one keyword per line.")
        return

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        keywords = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Loaded {len(keywords)} keywords from {input_file}.")

    # Load already processed keywords if resuming
    processed = set()
    file_exists = os.path.exists(output_file)
    if file_exists:
        with open(output_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "keyword" in row:
                    processed.add(row["keyword"])
        print(f"Found existing {len(processed)} analyzed keywords. Resuming remaining...")

    fieldnames = [
        "keyword", "score", "opportunity", "exact_title_matches",
        "forums_in_top10", "top_forum_rank", "has_search_demand",
        "top_ranking_title", "top_ranking_url"
    ]

    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(output_file) == 0:
            writer.writeheader()

        for count, kw in enumerate(keywords, 1):
            if kw in processed:
                continue

            print(f"[{count}/{len(keywords)}] Analyzing: {kw}")
            res = evaluate_keyword_gap(kw)
            if res:
                writer.writerow(res)
                f.flush()
                print(f"   -> Score: {res['score']}/100 | {res['opportunity']}")

            time.sleep(delay)

    print(f"\n🎉 Done! All results saved to {output_file}.")

if __name__ == "__main__":
    kw_file = sys.argv[1] if len(sys.argv) > 1 else "keywords.txt"
    run_bulk_gap_analysis(kw_file)
