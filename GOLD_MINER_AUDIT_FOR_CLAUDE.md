# 🪙 Gold Miner — System Architecture, Input Seeds, SERP Gap Engine & Raw Telemetry Audit Dossier

> **Confidential Technical Audit Document**  
> **Prepared for:** Deep Strategic & Code Review by Senior AI Architect (Claude)  
> **System Name:** Gold Miner (Autonomous Search Gap Radar & Stealth Swarm)  
> **Core Constraint:** **Strict $0.00 Infrastructure Spend** (Strictly zero paid API keys, zero commercial scrapers, zero paid proxies). Everything operates via automated headless HTTP protocols, public endpoints, and distributed GitHub Actions runners.  
> **Companion Dataset:** `raw_telemetry_samples.json` (80.5 KB full JSON database extract)

---

## 1. Executive Summary & Core Mission

**Gold Miner** is an autonomous market intelligence engine designed to discover **uncontested search voids ("Gold Mines")** on the internet.

### What is a "Search Gap Void"?
In organic search (Google & DuckDuckGo), when hundreds or thousands of users start searching for a specific long-tail problem, tool, or workaround, but **0 out of the top 10 ranking search results** feature that exact phrase in their HTML `<title>` tag, a **SERP Title Gap (Untouched Void)** exists.

Google is forced to rank generic articles, tangentially related documentation, or decade-old forum threads because **no developer has published a dedicated page, micro-tool, or cheatsheet targeting that exact phrase.** 

When an indie hacker or solo developer builds a lightweight single-page tool or markdown guide with that exact target title, their page effortlessly captures the #1 rank with minimal or zero backlinks due to **100% exact title match relevance**.

---

## 2. End-to-End System Architecture

```
[1. Frontier Seed Queue] (2,205 Niche Roots in 12 Evergreen Verticals)
            │
            ▼
[2. Google Trends Batch Probe] (today 12-m, 8-term batch exploration)
            │
            ├─► Extracts "RISING" (+% surge) & "BREAKOUT" (>5,000% velocity)
            └─► Extracts "TOP" (Established search volume index)
            │
            ▼
[3. Exclusion Shield] (Filters out navigational giants, adult terms, celebrity gossip)
            │
            ▼
[4. SERP Vulnerability Sieve] (DuckDuckGo HTML & Lite dual-endpoint organic scraper)
            │
            ├─► exact_title_matches: How many of top 10 contain exact phrase in <title>?
            ├─► root_domain_in_top5: Are naked homepages (e.g. site.com/) leaking into top 5?
            ├─► forum_count: Are Reddit / Quora / StackOverflow threads ranking in top 3?
            └─► stale_content: Are top ranking pages older than 2+ years?
            │
            ▼
[5. Developer Signal Collector] (GitHub Issues & StackOverflow public API checks)
            │
            ▼
[6. Composite Opportunity Scoring] (0 to 100 Gap Score)
            │   Final Gap Score = S_SERP (0-40) + S_Dev (0-30) + S_Velocity (0-30)
            │
            ▼
[7. Archetype Classification] (Micro-Tool, Workaround, Recipe, Breaking News)
            │
            ▼
[8. Distributed Cloud Fleet] (20 GitHub Actions shards disguised as enterprise telemetry)
```

---

## 3. The Input Problem: Seed Sources & Generic Noise

### The 12 Universal Evergreen Verticals
1. **Finance & Wealth**
2. **Small Business & B2B**
3. **Productivity & Work**
4. **Media & Converters**
5. **Health & Fitness**
6. **Real Estate & Living**
7. **Legal & Compliance**
8. **Academic & Education**
9. **Developer & Cloud**
10. **Gaming & Entertainment**
11. **E-Commerce & Selling**
12. **Travel & Visas**

---

### Where Did the Current 2,205 Frontier Seeds Come From?

Our system (`engines/taxonomy_loader.py`) populated seeds from 4 automated zero-cost sources:

1. **Handcrafted High-Intent Seed Anchors (`BASELINE_ROOT_SEEDS`):**
   - *Examples:* `"mortgage calculator"`, `"invoice generator"`, `"heic to jpg"`, `"calorie calculator"`, `"docker compose template"`, `"pokemon weakness chart"`.
   - *Verdict:* **High Quality.** These naturally expanded into high-intent long-tail voids like `"one rep max calculator rpe"`, `"pdf to word or text converter"`.

2. **StackOverflow Top Tags Scraper (`ingest_stackoverflow_tags`):**
   - *Mechanism:* Pulled the top 200 tags from StackOverflow API without authentication.
   - *Examples:* `image`, `forms`, `excel`, `css`, `algorithm`, `dictionary`, `load file`.
   - *The Problem:* **Excessive Generality.** A single noun like `image` or `forms` contains zero search intent. When passed into Google Trends, Google returns vague queries like `image tutorial`, `forms online`, or `what is an algorithm`.

3. **Wikipedia Category Crawlers (`ingest_wikipedia_categories`):**
   - *Mechanism:* Scraped top-level subcategories under academic and technical Wikipedia categories.
   - *Examples:* `alice`, `kno`, `legora`.
   - *The Problem:* Obscure proper nouns or acronyms that lack commercial or software utility.

4. **PyPI Top 500 Packages (`ingest_pypi_popular`):**
   - *Mechanism:* Extracted package names from PyPI's top download lists.
   - *Examples:* `requests`, `urllib3`, `pandas`.
   - *The Problem:* Often yields generic documentation lookups rather than high-margin developable tools.

---

### Observed Symptom: Categorization Mismatches
Because seeds were harvested automatically and matched by loose heuristics, several odd categorizations occurred:
* `a generation error occurred` &rarr; Classified under **Finance & Wealth** (triggered by parent seed `wealth` or financial trading error codes).
* `what are gen alphas` &rarr; Classified under **Finance & Wealth**.
* `load file in r` &rarr; Classified under **Legal & Compliance** (because `load file` is a legal e-discovery term, but in this query it's an R-programming command).
* `media error 1` &rarr; Classified under **Health & Fitness**.

---

## 4. Google Trends Extraction: Time Period Analysis

### Current Configuration
* **Endpoint:** Google Trends Batch Exploration API (`/trends/api/explore` & `/trends/api/widgetdata/relatedsearches`).
* **Time Window:** `today 12-m` (Past 12 Months, Worldwide).
* **Batch Size:** 5 to 8 keywords compared simultaneously per HTTP handshake to bypass rate limits.
* **Extraction Targets:**
  * `RISING` queries (queries that have experienced significant growth over the time window).
  * `BREAKOUT` queries (queries whose growth was >5,000%).
  * `TOP` queries (established baseline volume index 0–100).

---

### The Time Window Dilemma: 12-Month vs 6-Month vs 3-Month

| Time Window | Parameter | Pros | Cons | Recommendation Need |
| :--- | :--- | :--- | :--- | :--- |
| **Past 12 Months** *(Current)* | `today 12-m` | Eliminates seasonal blips; confirms true sustained search interest; high data volume. | Sluggish to detect immediate emerging software tools or new error codes from recent library releases (e.g. 2026/late 2025 releases). | Is it too stale? |
| **Past 6 Months** | `today 6-m` | Balanced medium; filters out 1-month viral fads while capturing emerging developer shifts. | Can still smooth out rapid breakout spikes that occurred in the last 60 days. | **Strong contender.** |
| **Past 3 Months** | `today 3-m` | Highly sensitive to new API changes, library deprecations, fresh software updates, and rapid breakouts. | Higher noise ratio; some breakouts might be short-lived bugs that get fixed in 2 weeks. | **Optimal for Workarounds & Breaking News.** |
| **Past 30 Days** | `today 1-m` | Captures hyper-fresh spikes. | Too much transient noise; high volatility; many terms have insufficient data in Trends. | Too noisy for long-term evergreen micro-tools. |

---

## 5. Live Database Evidence Snapshot

### Telemetry Matrix Summary (Current SQLite DB: `storage/telemetry_matrix.db`)
* **Total Evaluated Search Queries:** 2,059
* **Frontier Root Niche Pool:** 2,205
* **Genuinely Verified Untouched Voids (0/10 Title Matches):** 144
* **Competed Queries (1/10 to 10/10 Competitor Titles):** 175
* **Pending Live Audits (Awaiting SERP Scraping):** 1,740
* **Breakout Queries (>5,000% surge):** 75
* **Critical Gold Mines (Composite Score >= 85):** 4

---

### Top 10 Discovered 0/10 Untouched Voids

| Keyword | Category | Archetype | Gap Score | Trend Velocity | Top Ranking Competitor on Google | Real Gap Analysis |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **a generation error occurred** | Finance & Wealth | Workaround | **95** | BREAKOUT (+5,000%) | *"Backrooms: Generation Error Wiki | Fandom"* | **True Void.** High surge error query; #1 rank is a gaming wiki. No troubleshooting guide exists. |
| **heic error windows** | Media & Converters | Workaround | **85** | BREAKOUT (+5,000%) | *"How to Open iPhone HEIC Photos on Windows 11 and 10: HEIF Extension..."* | **True Void.** People search for the error fix; competitors only have generic "how to view" articles. |
| **calorie calculator net** | Health & Fitness | Micro-Tool | **85** | RISING (+680%) | *"Calorie Counting Made Easy - Online Calorie Counter"* | **Suspected Navigational.** User is likely searching for the domain `caloriecalculator.net`. Competitors omitted "net" in title. |
| **media error 1** | Health & Fitness | Workaround | **85** | BREAKOUT (+5,000%) | *"How to Fix Disk 1 Removable No Media Error [Detailed Guide]"* | **True Void.** Android MediaPlayer `error (1, -2147483648)` error code search without dedicated title target. |
| **what are gen alphas** | Finance & Wealth | Recipe | **85** | RISING (+760%) | *"Generation Alpha - Wikipedia"* | **Weak Commercial Value.** Pure definition search. Wiki ranks #1 without exact title phrase. |
| **affidavit of error form** | Legal & Compliance | Workaround | **80** | BREAKOUT (+5,000%) | *"Free Affidavit of Correction Form - PDF | Word - eForms"* | **True Void.** Legal form seekers search for "error form"; eForms targets "Correction Form". |
| **load file in r** | Legal & Compliance | Recipe | **80** | RISING (+600%) | *"How To Import Data from a File in R Programming"* | **True Void.** Coding snippet search; competitors use "Import Data" instead of exact "Load File in R". |
| **foreign exchange dealers** | Finance & Wealth | Recipe | **80** | RISING (+760%) | *"Top 10 Best Currency Exchange in DES MOINES, IA - Yelp"* | **Local / Commercial.** Google ranking local Yelp listings because no national directory targets the phrase. |
| **one rep max calculator rpe** | Health & Fitness | Micro-Tool | **75** | RISING (+520%) | *"RPE Calculator"* | **Pure Gold Mine.** Powerlifters wanting 1RM based on RPE scale; general 1RM calculators lack RPE title targeting. |
| **one rep max calculator accuracy** | Health & Fitness | Micro-Tool | **75** | RISING (+100%) | *"One Rep Max Calculator - Strength Level"* | **Pure Gold Mine.** Explores scientific formula comparisons (Brzycki vs Epley vs Lombardi). |

---

### Top 10 Competed Queries (Proving SERP Competition Sieve Accuracy)

| Keyword | Category | Exact Matches in Top 10 | Gap Score | Top Ranking Competitor on Google |
| :--- | :--- | :---: | :---: | :--- |
| **ups calculator vs nps** | Productivity & Work | **10 / 10** | 40 | *"NPS vs UPS Calculator 2026 - Compare National Pension vs Unified..."* |
| **webp vs png vs svg** | Media & Converters | **10 / 10** | 40 | *"SVG vs PNG vs WebP for Websites: Which Image Format to Use"* |
| **markdown editor linux** | Productivity & Work | **9 / 10** | 55 | *"11 Best Markdown Editors for Linux - It's FOSS"* |
| **video compressor free** | Media & Converters | **9 / 10** | 55 | *"Video Compressor | Reduce Video File Size Online - FreeConvert"* |
| **space colonization algorithm** | Developer & Cloud | **8 / 10** | 45 | *"Space Colonization Algorithm | danemerson13/space-colonization-py..."* |
| **m4a to mp3 free** | Media & Converters | **8 / 10** | 40 | *"M4A to MP3 Converter - FreeConvert.com"* |
| **webp vs png vs avif** | Media & Converters | **8 / 10** | 40 | *"Image Formats Compared — PNG vs JPEG vs WebP vs AVIF"* |
| **load file icon** | Legal & Compliance | **8 / 10** | 40 | *"Load file Icons & Symbols - Flaticon"* |
| **css design awards** | Developer & Cloud | **8 / 10** | 40 | *"CSS Design Awards - Website Awards - Best Web Design Inspiration"* |
| **m4a to mp3 windows** | Media & Converters | **7 / 10** | 60 | *"How can I convert m4a to mp3 on my Windows 11 PC?"* |

---

## 6. The Scoring Algorithm & Math

The Composite Opportunity Score (0 to 100) is calculated as:
$$\text{Final Gap Score} = S_{\text{SERP}} + S_{\text{Dev}} + S_{\text{Velocity}}$$

### 1. SERP Vulnerability Score ($S_{\text{SERP}}$: 0 to 40 Points)
* **Exact Title Match Count ($M$ in Top 10):**
  * $M = 0$: **+25 pts** (Untouched Void &mdash; zero competitors target this phrase)
  * $M = 1$: **+18 pts** (Extremely weak competition)
  * $M = 2$: **+10 pts** (Low competition)
  * $M \in [3, 4]$: **+5 pts** (Moderate competition)
  * $M \ge 5$: **0 pts** (Saturated)
* **Root Domain Mismatch Leak:** **+10 pts** if a naked homepage (e.g. `example.com/`) ranks in Top 5 for a 3+ word query.
* **Forum Leak Bonus:** **+10 pts** if Reddit, Quora, or StackOverflow ranks $\le 3$; **+5 pts** if in Top 10.
* **Stale Content Bonus:** **+5 pts** if top results are older than 2 years.

### 2. Developer Intent & Evidence Score ($S_{\text{Dev}}$: 0 to 30 Points)
* Active GitHub Issues with bug/unresolved labels: **+15 pts**
* StackOverflow unanswered or high-view questions: **+15 pts**

### 3. Trend Velocity Score ($S_{\text{Velocity}}$: 0 to 30 Points)
* `BREAKOUT` (>5,000% surge): **+30 pts**
* Rising $\ge +300\%$: **+20 pts**
* Rising $\ge +100\%$: **+10 pts**
* Established `TOP` volume query: **+5 pts**

---

## 7. Verbatim Raw JSON Telemetry Records (Live Data from SQLite)

Here are verbatim raw JSON objects straight from our SQLite database (`storage/telemetry_matrix.db`). These expose the exact data payload, including the full crawled SERP results, developer evidence signals, and score breakdowns.

### Sample A: The False-Positive Navigational Void (`calorie calculator net`)
*Notice the Bing ad click URL leak, and notice how 8 out of 10 organic URLs contain `.net` in their domain name!*

```json
{
  "id": 502,
  "keyword": "calorie calculator net",
  "category": "Health & Fitness",
  "trend_type": "RISING",
  "trend_velocity": "+680%",
  "gap_score": 85,
  "archetype": "Micro-Tool",
  "exact_title_matches": 0,
  "has_github_issues": 1,
  "has_stack_questions": 1,
  "top_competitor_title": "Calorie Counting Made Easy - Online Calorie Counter",
  "top_competitor_url": "https://duckduckgo.com/y.js?ad_domain=myfooddiary.com&ad_provider=bingv7aa&ad_type=txad&click_metadata=b_kGnuk8RjUbBvurIHyXHCPyD85lI%2D8D9PHo8v3yKoFBRm54mB4tv4iOvZoMSh7rGsJ_4%2DKVLMK3ErLG%2DJ3d2LKYOvnYqN4NLEyq3VZntpTfDo6dVN25%2Dui4ahWMZO6it7l2mTMjm7ueceKQNQtD_UIEFkfE16LAkT5%2Dv3A0E9k.e7Z%2DGeZ1OuNvROxVG%2DIXJA&rut=87d1c4d38c57208511b3a24463208c55bd6f44e301c56215b4587b7cd8257eb6&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fld%3De8eKqSFsa8TkYFXe6idJN_0TVUCUxVlgw0A4746RL0l31s2QE5_RTIiF5AUAWFa%2DLS2uR1XVRUjUsM7MLUlbK3IDywceI2tZ41RA4zJTloIN%2DYSYvsllVaSKnAUOvhd0oDdt0njdhoIBfa2BouMHT%2DYTL6iheJ0t6ilKu83Nu3Ax2bExR6meoqxTm9CRMFI7Wf4%2DGIoKuBe2DcPNgKu3h8vawBw8Q%26u%3DaHR0cHMlM2ElMmYlMmZ3d3cubXlmb29kZGlhcnkuY29tJTJmJTNmcWlkJTNkMiUyNm1zY2xraWQlM2QzNTVmODEzZWU0ZTkxYWFkYWFlOWViY2JlYjFlYWVmOCUyNnV0bV9zb3VyY2UlM2RiaW5nJTI2dXRtX21lZGl1bSUzZGNwYyUyNnV0bV9jYW1wYWlnbiUzZENhbG9yaWUlMjUyMC0lMjUyMFNlYXJjaCUyNnV0bV90ZXJtJTNkY2Fsb3JpZSUyNTIwY291bnRlciUyNnV0bV9jb250ZW50JTNkU0tBRyUyNTIwLSUyNTIwJTI1NUJjYWxvcmllJTI1MjBjb3VudGVyJTI1NUQ%26rlid%3D355f813ee4e91aadaae9ebcbeb1eaef8&vqd=4-302589648847944717431786570758100963652&iurl=%7B1%7DIG%3D854B6958867943FCBDFD759858F102F4%26CID%3D3F02BDE1C80B636430EAA5EEC9876241%26ID%3DDevEx%2C5037.1",
  "human_verdict": "pending",
  "first_seen": "2026-11-12 01:01:47",
  "last_updated": "2026-11-12 01:01:47",
  "evidence": {
    "serp": {
      "query": "calorie calculator net",
      "serp_score": 35,
      "exact_title_matches": 0,
      "root_domain_in_top5": true,
      "forum_count": 0,
      "top_forum_rank": null,
      "has_stale_content": false,
      "results_count": 10,
      "top_competitor_title": "Calorie Counting Made Easy - Online Calorie Counter",
      "top_competitor_url": "https://duckduckgo.com/y.js?ad_domain=myfooddiary.com&ad_provider=bingv7aa&ad_type=txad&click_metadata=b_kGnuk8RjUbBvurIHyXHCPyD85lI%2D8D9PHo8v3yKoFBRm54mB4tv4iOvZoMSh7rGsJ_4%2DKVLMK3ErLG%2DJ3d2LKYOvnYqN4NLEyq3VZntpTfDo6dVN25%2Dui4ahWMZO6it7l2mTMjm7ueceKQNQtD_UIEFkfE16LAkT5%2Dv3A0E9k.e7Z%2DGeZ1OuNvROxVG%2DIXJA&rut=87d1c4d38c57208511b3a24463208c55bd6f44e301c56215b4587b7cd8257eb6&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fld%3De8eKqSFsa8TkYFXe6idJN_0TVUCUxVlgw0A4746RL0l31s2QE5_RTIiF5AUAWFa%2DLS2uR1XVRUjUsM7MLUlbK3IDywceI2tZ41RA4zJTloIN%2DYSYvsllVaSKnAUOvhd0oDdt0njdhoIBfa2BouMHT%2DYTL6iheJ0t6ilKu83Nu3Ax2bExR6meoqxTm9CRMFI7Wf4%2DGIoKuBe2DcPNgKu3h8vawBw8Q%26u%3DaHR0cHMlM2ElMmYlMmZ3d3cubXlmb29kZGlhcnkuY29tJTJmJTNmcWlkJTNkMiUyNm1zY2xraWQlM2QzNTVmODEzZWU0ZTkxYWFkYWFlOWViY2JlYjFlYWVmOCUyNnV0bV9zb3VyY2UlM2RiaW5nJTI2dXRtX21lZGl1bSUzZGNwYyUyNnV0bV9jYW1wYWlnbiUzZENhbG9yaWUlMjUyMC0lMjUyMFNlYXJjaCUyNnV0bV90ZXJtJTNkY2Fsb3JpZSUyNTIwY291bnRlciUyNnV0bV9jb250ZW50JTNkU0tBRyUyNTIwLSUyNTIwJTI1NUJjYWxvcmllJTI1MjBjb3VudGVyJTI1NUQ%26rlid%3D355f813ee4e91aadaae9ebcbeb1eaef8&vqd=4-302589648847944717431786570758100963652&iurl=%7B1%7DIG%3D854B6958867943FCBDFD759858F102F4%26CID%3D3F02BDE1C80B636430EAA5EEC9876241%26ID%3DDevEx%2C5037.1",
      "raw_results": [
        {
          "title": "Calorie Counting Made Easy - Online Calorie Counter",
          "url": "https://duckduckgo.com/y.js?ad_domain=myfooddiary.com&ad_provider=bingv7aa&ad_type=txad&click_metadata=b_kGnuk8RjUbBvurIHyXHCPyD85lI%2D8D9PHo8v3yKoFBRm54mB4tv4iOvZoMSh7rGsJ_4%2DKVLMK3ErLG%2DJ3d2LKYOvnYqN4NLEyq3VZntpTfDo6dVN25%2Dui4ahWMZO6it7l2mTMjm7ueceKQNQtD_UIEFkfE16LAkT5%2Dv3A0E9k.e7Z%2DGeZ1OuNvROxVG%2DIXJA&rut=87d1c4d38c57208511b3a24463208c55bd6f44e301c56215b4587b7cd8257eb6&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fld%3De8eKqSFsa8TkYFXe6idJN_0TVUCUxVlgw0A4746RL0l31s2QE5_RTIiF5AUAWFa%2DLS2uR1XVRUjUsM7MLUlbK3IDywceI2tZ41RA4zJTloIN%2DYSYvsllVaSKnAUOvhd0oDdt0njdhoIBfa2BouMHT%2DYTL6iheJ0t6ilKu83Nu3Ax2bExR6meoqxTm9CRMFI7Wf4%2DGIoKuBe2DcPNgKu3h8vawBw8Q%26u%3DaHR0cHMlM2ElMmYlMmZ3d3cubXlmb29kZGlhcnkuY29tJTJmJTNmcWlkJTNkMiUyNm1zY2xraWQlM2QzNTVmODEzZWU0ZTkxYWFkYWFlOWViY2JlYjFlYWVmOCUyNnV0bV9zb3VyY2UlM2RiaW5nJTI2dXRtX21lZGl1bSUzZGNwYyUyNnV0bV9jYW1wYWlnbiUzZENhbG9yaWUlMjUyMC0lMjUyMFNlYXJjaCUyNnV0bV90ZXJtJTNkY2Fsb3JpZSUyNTIwY291bnRlciUyNnV0bV9jb250ZW50JTNkU0tBRyUyNTIwLSUyNTIwJTI1NUJjYWxvcmllJTI1MjBjb3VudGVyJTI1NUQ%26rlid%3D355f813ee4e91aadaae9ebcbeb1eaef8&vqd=4-302589648847944717431786570758100963652&iurl=%7B1%7DIG%3D854B6958867943FCBDFD759858F102F4%26CID%3D3F02BDE1C80B636430EAA5EEC9876241%26ID%3DDevEx%2C5037.1",
          "snippet": ""
        },
        {
          "title": "Calorie Calculator",
          "url": "https://www.calculator.net/calorie-calculator.html",
          "snippet": ""
        },
        {
          "title": "Calorie Calculator: Calculate Your Daily Calorie Intake & Macros",
          "url": "https://calorie-calculator.net/",
          "snippet": ""
        },
        {
          "title": "calorie-calculator",
          "url": "https://calculator-net.com/calorie-calculator/",
          "snippet": ""
        },
        {
          "title": "Calorie Calculator",
          "url": "https://www.netcalculator.net/2025/10/calorie-calculator.html",
          "snippet": ""
        },
        {
          "title": "Calories Calculator",
          "url": "https://www.caloriescalculator.net/",
          "snippet": ""
        },
        {
          "title": "TDEE Calculator: Learn Your Total Daily Energy Expenditure",
          "url": "https://tdeecalculator.net/",
          "snippet": ""
        },
        {
          "title": "Calorie Deficit Calculator",
          "url": "https://calculator-online.net/calorie-deficit-calculator/",
          "snippet": ""
        },
        {
          "title": "Calorie Calculator - Mayo Clinic",
          "url": "https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/calorie-calculator/itt-20402304",
          "snippet": ""
        },
        {
          "title": "Fitness and Health Calculators",
          "url": "https://www.calculator.net/fitness-and-health-calculator.html",
          "snippet": ""
        }
      ]
    },
    "dev": {
      "query": "calorie calculator net",
      "dev_score": 30,
      "stack_exchange": {
        "unresolved_count": 1,
        "total_items": 1,
        "has_unresolved": true,
        "sample_title": "Copying cell data based on a changing date"
      },
      "github": {
        "open_issues_count": 36,
        "repos_count": 23,
        "is_solution_gap": false,
        "has_github_issues": true
      },
      "hacker_news": {
        "hn_discussions": 5,
        "total_comments": 12,
        "has_sentiment": true
      },
      "has_stack_questions": true,
      "has_github_issues": true
    },
    "score_breakdown": {
      "serp": 35,
      "dev": 30,
      "velocity": 20
    },
    "parent_niche": "calorie calculator",
    "shard_id": 2
  }
}
```

---

### Sample B: The True Workaround Void (`heic error windows`)
*Notice how competitors rank for general viewing/opening tutorials, but none target the error troubleshooting intent!*

```json
{
  "id": 400,
  "keyword": "heic error windows",
  "category": "Media & Converters",
  "trend_type": "BREAKOUT",
  "trend_velocity": "BREAKOUT",
  "gap_score": 85,
  "archetype": "Workaround",
  "exact_title_matches": 0,
  "has_github_issues": 1,
  "has_stack_questions": 1,
  "top_competitor_title": "How to Open iPhone HEIC Photos on Windows 11 and 10: HEIF Extension ...",
  "top_competitor_url": "https://windowsforum.com/tutorials/how-to-open-iphone-heic-photos-on-windows-11-and-10-heif-extension-photos-repair-and-fixes.447206/",
  "human_verdict": "pending",
  "first_seen": "2026-11-11 21:59:00",
  "last_updated": "2026-11-11 21:59:00",
  "evidence": {
    "serp": {
      "query": "heic error windows",
      "serp_score": 35,
      "exact_title_matches": 0,
      "root_domain_in_top5": false,
      "forum_count": 3,
      "top_forum_rank": 1,
      "has_stale_content": false,
      "results_count": 10,
      "top_competitor_title": "How to Open iPhone HEIC Photos on Windows 11 and 10: HEIF Extension ...",
      "top_competitor_url": "https://windowsforum.com/tutorials/how-to-open-iphone-heic-photos-on-windows-11-and-10-heif-extension-photos-repair-and-fixes.447206/",
      "raw_results": [
        {
          "title": "How to Open iPhone HEIC Photos on Windows 11 and 10: HEIF Extension ...",
          "url": "https://windowsforum.com/tutorials/how-to-open-iphone-heic-photos-on-windows-11-and-10-heif-extension-photos-repair-and-fixes.447206/",
          "snippet": ""
        },
        {
          "title": "HEIC File Won't Open on Windows? Here's the Fix - SnapHEIC",
          "url": "https://snapheic.com/guides/heic-file-wont-open-on-windows",
          "snippet": ""
        },
        {
          "title": "Can't Open HEIC Files on Windows? Here's How to Fix It - MUO",
          "url": "https://www.makeuseof.com/cant-open-heic-files-on-windows-heres-how-to-fix-it/",
          "snippet": ""
        },
        {
          "title": "Why HEIC won't open on Windows 11 (and the actual fix)",
          "url": "https://heicpix.com/blog/why-heic-wont-open-on-windows-11/",
          "snippet": ""
        },
        {
          "title": "HEIC image extension not working on Windows 11, are there any heic ...",
          "url": "https://techcommunity.microsoft.com/discussions/windows11/heic-image-extension-not-working-on-windows-11-are-there-any-heic-extension-alte/4387238",
          "snippet": ""
        },
        {
          "title": "Can't open HEIC photos even with HEVC and HEIF extension installed",
          "url": "https://learn.microsoft.com/en-us/answers/questions/4022451/cant-open-heic-photos-even-with-hevc-and-heif-exte",
          "snippet": ""
        },
        {
          "title": "Photos app Video Editor error: Can't view this file type",
          "url": "https://support.microsoft.com/en-us/windows/apps/photos/photos-app-video-editor-error-can-t-view-this-file-type",
          "snippet": ""
        },
        {
          "title": "HEIF/HEIC only opening on some Windows PCs | Microsoft Community Hub",
          "url": "https://techcommunity.microsoft.com/discussions/windows11/heifheic-only-opening-on-some-windows-pcs/4436081",
          "snippet": ""
        },
        {
          "title": "3 Solutions to Can't Open HEIC File on Windows 10/11 - FoneTool",
          "url": "https://www.fonetool.com/phone-management/cant-open-heic-file.html",
          "snippet": ""
        },
        {
          "title": "Unable to Install HEIF Image Extensions (HEIC Codec) Due to Microsoft ...",
          "url": "https://learn.microsoft.com/en-us/answers/questions/5853241/unable-to-install-heif-image-extensions-heic-codec",
          "snippet": ""
        }
      ]
    },
    "dev": {
      "query": "heic error windows",
      "dev_score": 30,
      "stack_exchange": {
        "unresolved_count": 3,
        "total_items": 8,
        "has_unresolved": true,
        "sample_title": "Imagick .heic format not supported in php (xampp) but in console"
      },
      "github": {
        "open_issues_count": 462,
        "repos_count": 7,
        "is_solution_gap": true,
        "has_github_issues": true
      },
      "hacker_news": {
        "hn_discussions": 3,
        "total_comments": 0,
        "has_sentiment": false
      },
      "has_stack_questions": true,
      "has_github_issues": true
    },
    "score_breakdown": {
      "serp": 0,
      "dev": 30,
      "velocity": 30
    },
    "parent_niche": "heic to jpg",
    "shard_id": 0
  }
}
```

---

### Sample C: The True Micro-Tool Void (`one rep max calculator rpe`)
*Notice how competitors are general 1RM calculators, missing the specific RPE modifier!*

```json
{
  "id": 558,
  "keyword": "one rep max calculator rpe",
  "category": "Health & Fitness",
  "trend_type": "RISING",
  "trend_velocity": "+520%",
  "gap_score": 75,
  "archetype": "Micro-Tool",
  "exact_title_matches": 0,
  "has_github_issues": 0,
  "has_stack_questions": 1,
  "top_competitor_title": "RPE Calculator",
  "top_competitor_url": "https://www.rpecalculator.com/",
  "human_verdict": "pending",
  "first_seen": "2026-11-12 01:04:12",
  "last_updated": "2026-11-12 01:04:12",
  "evidence": {
    "serp": {
      "query": "one rep max calculator rpe",
      "serp_score": 35,
      "exact_title_matches": 0,
      "root_domain_in_top5": true,
      "forum_count": 0,
      "top_forum_rank": null,
      "has_stale_content": false,
      "results_count": 10,
      "top_competitor_title": "RPE Calculator",
      "top_competitor_url": "https://www.rpecalculator.com/",
      "raw_results": [
        {
          "title": "RPE Calculator",
          "url": "https://www.rpecalculator.com/",
          "snippet": ""
        },
        {
          "title": "1RM Calculator with RPE | Strength Training & Powerlifting Tool",
          "url": "https://maxrep.net/en/1rm-rpe-calculator",
          "snippet": ""
        },
        {
          "title": "RPE Calculator: The Complete Autoregulated Training Guide",
          "url": "https://onerepmaxcalculators.com/rpe-calculator/",
          "snippet": ""
        },
        {
          "title": "One Rep Max Calculator - Strength Level",
          "url": "https://strengthlevel.com/one-rep-max-calculator",
          "snippet": ""
        },
        {
          "title": "RPE Calculator Tool - Easily Calculate RPE (2026) - Lift Vault",
          "url": "https://liftvault.com/resources/rpe-one-rep-max-conversion-calculator/",
          "snippet": ""
        },
        {
          "title": "RPE Calculator",
          "url": "https://www.liftmath.com/",
          "snippet": ""
        },
        {
          "title": "RPE Calculator - Rate of Perceived Exertion Tool",
          "url": "https://infinitycalculator.com/sports/rpe-calculator",
          "snippet": ""
        },
        {
          "title": "RPE Load Calculator - PLSource",
          "url": "https://www.plsource.org/rpe-calc/",
          "snippet": ""
        },
        {
          "title": "RPE Calculator: Estimate 1RM & Target Weights (RTS Chart)",
          "url": "https://www.rpe-calculator.net/",
          "snippet": ""
        },
        {
          "title": "RPE Calculator \u2014 Convert RPE and Reps to %1RM and Estimated Max ...",
          "url": "https://performmath.com/rpe-calculator",
          "snippet": ""
        }
      ]
    },
    "dev": {
      "query": "one rep max calculator rpe",
      "dev_score": 20,
      "stack_exchange": {
        "unresolved_count": 5,
        "total_items": 5,
        "has_unresolved": true,
        "sample_title": "one rep max calculator"
      },
      "github": {
        "open_issues_count": 0,
        "repos_count": 0,
        "is_solution_gap": false,
        "has_github_issues": false
      },
      "hacker_news": {
        "hn_discussions": 5,
        "total_comments": 0,
        "has_sentiment": false
      },
      "has_stack_questions": true,
      "has_github_issues": false
    },
    "score_breakdown": {
      "serp": 35,
      "dev": 20,
      "velocity": 20
    },
    "parent_niche": "one rep max calculator",
    "shard_id": 2
  }
}
```

---

### Sample D: The Heavily Competed Query (`ups calculator vs nps`)
*Notice how 10 out of 10 competitors explicitly target the comparison in their page title!*

```json
{
  "id": 1154,
  "keyword": "ups calculator vs nps",
  "category": "Productivity & Work",
  "trend_type": "RISING",
  "trend_velocity": "+100%",
  "gap_score": 40,
  "archetype": "Micro-Tool",
  "exact_title_matches": 10,
  "has_github_issues": 1,
  "has_stack_questions": 1,
  "top_competitor_title": "NPS vs UPS Calculator 2026 - Compare National Pension vs Unified ...",
  "top_competitor_url": "https://npscalculators.in/nps-vs-ups-calculator/",
  "human_verdict": "pending",
  "first_seen": "2026-11-12 07:01:41",
  "last_updated": "2026-11-12 07:01:41",
  "evidence": {
    "serp": {
      "query": "ups calculator vs nps",
      "serp_score": 0,
      "exact_title_matches": 10,
      "root_domain_in_top5": false,
      "forum_count": 0,
      "top_forum_rank": null,
      "has_stale_content": false,
      "results_count": 10,
      "top_competitor_title": "NPS vs UPS Calculator 2026 - Compare National Pension vs Unified ...",
      "top_competitor_url": "https://npscalculators.in/nps-vs-ups-calculator/",
      "raw_results": [
        {
          "title": "NPS vs UPS Calculator 2026 - Compare National Pension vs Unified ...",
          "url": "https://npscalculators.in/nps-vs-ups-calculator/",
          "snippet": ""
        },
        {
          "title": "UPS vs NPS Pension Calculator 2025 - Smartprix",
          "url": "https://www.smartprix.com/ups-vs-nps",
          "snippet": ""
        },
        {
          "title": "NPS vs UPS Calculator - Compare Pension Schemes | CalculatorHari.com",
          "url": "https://calculatorhari.com/nps-vs-ups-calculator.html",
          "snippet": ""
        },
        {
          "title": "UPS vs NPS Calculator 2026 \u2014 Unified Pension Scheme Payout ...",
          "url": "https://fincalculator.in/ups-vs-nps-calculator",
          "snippet": ""
        },
        {
          "title": "UPS vs NPS Calculator 2026: Which Pension Is Better for You?",
          "url": "https://npscalculator.org.in/ups-vs-nps-calculator/",
          "snippet": ""
        },
        {
          "title": "Calculator: UPS vs. NPS - which is better? - Arthgyaan",
          "url": "https://arthgyaan.com/blog/calculator-ups-vs-nps-which-is-better.html",
          "snippet": ""
        },
        {
          "title": "Retirement Calculator (NPS vs UPS) - assetyogi.com",
          "url": "https://assetyogi.com/calculators/retirement-calculator/",
          "snippet": ""
        },
        {
          "title": "UPS vs NPS Calculator 2026 \u2014 Which Pays More?",
          "url": "https://8thcpc.co.in/calc-ups-nps.html",
          "snippet": ""
        },
        {
          "title": "NPS vs UPS Calculator - Which Pension Is Better? | WorkCalcs",
          "url": "https://workcalcs.com/nps-vs-ups-calculator/",
          "snippet": ""
        },
        {
          "title": "NPS vs UPS Calculator 2026 \u2014 Government Employee Pension Comparison ...",
          "url": "https://asymmetrica.in/calculators/nps-vs-ups/",
          "snippet": ""
        }
      ]
    },
    "dev": {
      "query": "ups calculator vs nps",
      "dev_score": 30,
      "stack_exchange": {
        "unresolved_count": 16,
        "total_items": 24,
        "has_unresolved": true,
        "sample_title": "Errors when Building up a Custom Loss Function"
      },
      "github": {
        "open_issues_count": 16,
        "repos_count": 7,
        "is_solution_gap": true,
        "has_github_issues": true
      },
      "hacker_news": {
        "hn_discussions": 5,
        "total_comments": 0,
        "has_sentiment": false
      },
      "has_stack_questions": true,
      "has_github_issues": true
    },
    "score_breakdown": {
      "serp": 0,
      "dev": 30,
      "velocity": 10
    },
    "parent_niche": "calculator",
    "shard_id": 2
  }
}
```

---

## 8. Core Engine Python Code (Under the Hood)

Below is the exact production Python code governing Seed Ingestion, SERP Auditing, and Scoring.

### Engine Module 1: Seed Harvesting & Taxonomies (`engines/taxonomy_loader.py`)

```python
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


# Disguised telemetry alias
TaxonomyLoader = NicheIngestor


if __name__ == "__main__":
    ingestor = NicheIngestor()
    stats = ingestor.run_all()
    frontier_stats = db.get_frontier_stats()
    print("\n--- INGESTION COMPLETE ---")
    print(f"Sources yield: {stats}")
    print(f"Frontier Queue Telemetry: Total={frontier_stats['total']}, Pending={frontier_stats['pending']}")
    print(f"Categories Breakdown: {frontier_stats['by_category']}")

```

---

### Engine Module 2: SERP Scraping & Title Competition Sieve (`engines/index_auditor.py`)

```python
"""
Free DuckDuckGo HTML SERP Auditor (Dual-Evidence Layer 3A)
Zero-cost, zero-API-key organic SERP screen measuring:
- Exact <title> match voids (0/10 = void, 1/10 = vulnerable, >=4/10 = saturated)
- Root domain mismatches (naked homepages ranking for deep queries)
- Forum / weak platform ranking signals (Reddit, StackOverflow, Quora, Medium)
- Top ranking competitor titles & URLs
"""

import logging
import random
import re
import ssl
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("serp_sieve")

# Create unverified SSL context for macOS certificate compatibility
SSL_CTX = ssl._create_unverified_context()

# Domains that represent user discussion rather than dedicated technical tools/guides
FORUM_AND_WEAK_DOMAINS = [
    "reddit.com",
    "quora.com",
    "medium.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
    "discussions.apple.com",
    "community.cloudflare.com",
    "forum.",
    "community.",
    "answers.microsoft.com",
    "dev.to",
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class SerpSieve:
    def __init__(self):
        pass

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duckduckgo.com/",
        }

    def fetch_serp(self, query: str) -> List[Dict[str, str]]:
        """
        Fetches top 10 organic results from DuckDuckGo HTML endpoint,
        falling back to the lightweight lite.duckduckgo.com endpoint if primary is rate-limited.
        """
        time.sleep(random.uniform(0.3, 0.7))
        results: List[Dict[str, str]] = []

        # 1. Primary: html.duckduckgo.com
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            blocks = re.findall(r'<div class="result results_links.*?\">(.*?)</div>\s*</div>', html, re.DOTALL)
            for b in blocks[:10]:
                m_url = re.search(r"uddg=([^&]+)", b)
                m_title = re.search(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', b, re.DOTALL)
                m_snippet = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', b, re.DOTALL)

                if m_url and m_title:
                    try:
                        real_url = urllib.parse.unquote(m_url.group(1))
                        clean_title = unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip()
                        snippet = unescape(re.sub(r"<[^>]+>", "", m_snippet.group(1))).strip() if m_snippet else ""
                        results.append({"title": clean_title, "url": real_url, "snippet": snippet})
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML SERP primary fetch failed for '{query}': {e}")

        # 2. Resilient Fallback: lite.duckduckgo.com (Different server infrastructure, fewer blocks)
        if not results:
            try:
                lite_url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
                lite_req = urllib.request.Request(lite_url, headers=self._get_headers())
                with urllib.request.urlopen(lite_req, context=SSL_CTX, timeout=5) as resp:
                    lite_html = resp.read().decode("utf-8", errors="ignore")

                matches = re.findall(r'<a\s+[^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*class=[\'\"]result-link[\'\"][^>]*>(.*?)</a>', lite_html, re.DOTALL)
                for href, title in matches:
                    if "duckduckgo-help-pages" in href or "more info" in title.lower() or "y.js" in href:
                        continue
                    m = re.search(r"uddg=([^&]+)", href)
                    real_url = urllib.parse.unquote(m.group(1)) if m else href
                    clean_title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
                    results.append({"title": clean_title, "url": real_url, "snippet": ""})
                    if len(results) >= 10:
                        break
            except Exception as e:
                logger.debug(f"DuckDuckGo Lite fallback fetch failed for '{query}': {e}")

        return results

    def audit(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Convenience alias for audit_serp."""
        return self.audit_serp(query, serp_results=serp_results)

    def audit_serp(self, query: str, serp_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Calculates SERP Vulnerability metrics:
        - exact_title_matches
        - root_domain_in_top5
        - forum_count
        - top_forum_rank
        - serp_vulnerability_score (0 to 40 pts)
        """
        results = serp_results if serp_results is not None else self.fetch_serp(query)

        # Guard: If no results could be retrieved (e.g. rate-limit or timeout), do NOT claim untouched void!
        if not results:
            return {
                "query": query,
                "serp_score": 0,
                "exact_title_matches": None,
                "root_domain_in_top5": False,
                "forum_count": 0,
                "top_forum_rank": None,
                "has_stale_content": False,
                "results_count": 0,
                "top_competitor_title": "",
                "top_competitor_url": "",
                "raw_results": [],
            }

        q_lower = query.lower().strip()
        q_tokens = [t for t in q_lower.split() if len(t) > 2]

        exact_title_count = 0
        root_domain_count_top5 = 0
        forum_count = 0
        top_forum_rank: Optional[int] = None
        has_stale_content = False

        current_year = 2026
        stale_years = [str(y) for y in range(2015, current_year - 1)]

        for idx, item in enumerate(results):
            rank = idx + 1
            title_lower = item["title"].lower()
            url_lower = item["url"].lower()
            snippet = item.get("snippet", "").lower()

            # 1. Exact or near-exact title match
            if q_lower in title_lower:
                exact_title_count += 1
            elif len(q_tokens) >= 3 and sum(1 for t in q_tokens if t in title_lower) == len(q_tokens):
                # All major tokens appear in title
                exact_title_count += 1

            # 2. Root domain mismatch (naked domain ranking in top 5 for multi-word query)
            if rank <= 5 and len(q_tokens) >= 3:
                try:
                    parsed = urlparse(item["url"])
                    path = parsed.path.strip("/")
                    if not path or path == "":
                        root_domain_count_top5 += 1
                except Exception:
                    pass

            # 3. Forum / Discussion ranking
            is_forum = any(d in url_lower for d in FORUM_AND_WEAK_DOMAINS)
            if is_forum:
                forum_count += 1
                if top_forum_rank is None:
                    top_forum_rank = rank

            # 4. Content freshness check (>2 years old)
            for yr in stale_years:
                if yr in snippet or yr in title_lower:
                    has_stale_content = True
                    break

        # Calculate SERP Vulnerability Points (Max 40 pts according to Master Plan)
        serp_score = 0
        if exact_title_count == 0:
            serp_score += 25  # Zero competitors have targeted this exact phrase
        elif exact_title_count == 1:
            serp_score += 18  # Only 1 competitor, very vulnerable
        elif exact_title_count <= 2:
            serp_score += 10
        elif exact_title_count <= 4:
            serp_score += 5

        # Root domain leak in top 5 (+10 pts)
        if root_domain_count_top5 >= 1:
            serp_score += 10

        # Forum ranking in top 3 gives bonus vulnerability
        if top_forum_rank and top_forum_rank <= 3:
            serp_score = min(40, serp_score + 10)
        elif forum_count >= 1:
            serp_score = min(40, serp_score + 5)

        # Stale content (+5 pts)
        if has_stale_content:
            serp_score = min(40, serp_score + 5)

        top_title = results[0]["title"] if results else ""
        top_url = results[0]["url"] if results else ""

        return {
            "query": query,
            "serp_score": min(40, serp_score),
            "exact_title_matches": exact_title_count,
            "root_domain_in_top5": root_domain_count_top5 > 0,
            "forum_count": forum_count,
            "top_forum_rank": top_forum_rank,
            "has_stale_content": has_stale_content,
            "results_count": len(results),
            "top_competitor_title": top_title,
            "top_competitor_url": top_url,
            "raw_results": results,
        }

    # Alias for convenience
    audit = audit_serp


# Disguised telemetry alias
IndexAuditor = SerpSieve


if __name__ == "__main__":
    sieve = SerpSieve()
    audit = sieve.audit_serp("fastapi jwt refresh token boilerplate")
    print(f"Query: {audit['query']}")
    print(f"SERP Vulnerability Score: {audit['serp_score']}/40")
    print(f"Exact Title Matches: {audit['exact_title_matches']}")
    print(f"Forums in Top 10: {audit['forum_count']}")
    print(f"Top Result: {audit['top_competitor_title']} ({audit['top_competitor_url']})")

```

---

### Engine Module 3: Composite Opportunity Evaluator (`engines/evaluator.py`)

```python
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
from typing import Any, Dict, Optional, Tuple

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
    Accepts both standard and legacy keyword arguments.
    """
    q = query or keyword or ""
    audit = serp_audit or serp_data or {}
    evidence = dev_evidence or {}

    s_serp = serp_score if serp_score is not None else audit.get("serp_score", 0)
    s_dev = dev_score if dev_score is not None else evidence.get("dev_score", 0)
    s_velocity = calculate_velocity_score(trend_type, trend_velocity)

    final_score = min(100, s_serp + s_dev + s_velocity)
    archetype, deliverable = classify_archetype(q)

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

```

---

## 9. Specific Code, Regex & Logic Flaws Identified for Review

Based on our raw data inspection, here are 5 specific logical and algorithmic vulnerabilities we need Claude to fix:

### Flaw 1: DuckDuckGo Ad URL Leakage into Organic SERP
In `calorie calculator net` (Sample A), Result #0 was:
`url: "https://duckduckgo.com/y.js?ad_domain=myfooddiary.com&ad_provider=bingv7aa..."`
DuckDuckGo ad redirects (`y.js`, `duckduckgo.com/y.js`) leaked into the organic results array because `fetch_serp` regex did not filter out sponsored links!

### Flaw 2: Navigational TLD Leakage (`.net`, `.com`, `.org`)
`calorie calculator net` scored 0/10 title matches because competitors had titles like `"Calorie Calculator"`, but their domain names were `calculator.net`, `calorie-calculator.net`, `tdeecalculator.net`. The searcher simply appended "net" to locate a domain. We need a domain-collision filter!

### Flaw 3: StackOverflow Single-Word Tags Producing Intent-Free Noise
In `taxonomy_loader.py`, `ingest_stackoverflow_tags()` inserts single nouns: `image`, `forms`, `excel`, `css`, `algorithm`. These contain zero action intent, polluting the frontier queue.

### Flaw 4: Loose Dev Evidence Token Matching
In `calorie calculator net`, the Dev Evidence Collector searched StackExchange and matched an irrelevant Excel question: `"Copying cell data based on a changing date"`, awarding +15 unearned points! Dev evidence queries must enforce strict phrase matching or relevance thresholds.

### Flaw 5: Category Classification Drift
Because categories are inherited from the parent seed, queries often inherit incorrect categories (e.g. `a generation error occurred` inherited `Finance & Wealth` because parent seed was `trading room`).

---

## 10. The 6 Critical Architectural Questions for Claude

Please review the architecture, raw data, and code above and provide strategic, mathematically grounded recommendations for the following 6 areas:

### Question 1: How should we overhaul our Input Seed Sources to eliminate generic keywords?
* How can we automatically harvest 10,000+ **intent-rich seed anchors** without human hardcoding, while avoiding single-word nouns like `image`, `forms`, `health`, and `css`?
* What specific zero-cost public endpoints or scrapers would you recommend? (e.g., Google Autocomplete alphanumeric tree scrapers `keyword + a..z`, Reddit pain-point scrapers, GitHub trending topics, npm error telemetry, HuggingFace model names, ProductHunt taxonomy, Wikipedia "Lists of...", etc.)?
* What regex or programmatic filters should we apply to guarantee that every seed has **clear buildable intent** (e.g. requires action verbs, comparative markers, problem prefixes, or modifier suffixes)?

### Question 2: Should we reduce the Google Trends time window from 12 months to 6 months or 3 months?
* What is the quantitative tradeoff between `today 12-m`, `today 6-m`, and `today 3-m`?
* Would a **Two-Tier Hybrid Window** work better?
  * *Discovery Tier:* Scan Google Trends on `today 3-m` to detect explosive immediate breakouts.
  * *Validation Tier:* If a breakout is found, query `today 12-m` to verify if it has a non-zero historical baseline or if it's a 3-day viral flash in the pan.
* What exact Trends parameters yield the highest signal-to-noise ratio for software builders?

### Question 3: How should we filter out "False Positive" Title Voids?
* How can we programmatically detect and downrank:
  1. **Navigational queries for domain extensions** (`.net`, `.com`, `.org`, `.io`, `login`, `portal`, `website`)?
  2. **Brand abbreviations and company names** (e.g. `ms` &rarr; Microsoft, `fb` &rarr; Facebook, `aws` &rarr; Amazon)?
* Can you provide a drop-in Python function that checks if the crawled SERP domains or URLs match the query tokens?

### Question 4: How can we fix categorization and archetype mapping?
* How should we accurately classify queries into the 12 Universal Verticals dynamically without paid AI APIs?
* Should we use Bayesian token probability, keyword heuristics, or classify based on the meta-descriptions and domains of the top 5 SERP competitors?

### Question 5: How can we scale the Frontier Pool from 2,205 to 50,000+ niches on $0.00 infrastructure?
* Currently, 20 GitHub Actions runner shards run periodically across 5 repositories.
* How can we structure seed scheduling, cooldown intervals (e.g. 90-day cooldown), and recursive tree expansion (extracting rising queries as new parent seeds for Level 2 exploration) without triggering Google Trends rate limits?

### Question 6: What are the highest-converting Developable Archetypes for 2026?
* We currently map into 4 archetypes: *Micro-Tool*, *Workaround*, *Recipe*, and *Breaking News*.
* For a solo indie developer building programmatic SEO sites or micro-SaaS utilities, which archetypes have the highest traffic-to-revenue conversion?
* Are there additional archetypes we should introduce (e.g., *Interactive Visualizer*, *Config Generator*, *Compliance Checklist*, *Cost Estimator*)?

---

## 11. Summary of Required Deliverables from Claude

When responding, please deliver:
1. **Concrete Architecture Recommendations** for the 6 questions above.
2. **Actionable Python Code / Regex Snippets** that we can drop directly into `engines/taxonomy_loader.py`, `engines/index_auditor.py`, and `engines/evaluator.py` to fix:
   - Ad link filtering in SERP scraping.
   - Domain extension / navigational false positive detection.
   - Strict dev evidence matching.
   - Intent-rich seed expansion.
3. **A Clear Verdict on the Google Trends Time Window** (`today 12-m` vs `today 6-m` vs `today 3-m` vs Hybrid).
4. **Specific New Seed Harvesting Sources** that operate at $0.00 cost with zero API keys.
