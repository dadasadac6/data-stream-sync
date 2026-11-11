# Universal Search Gap Radar & Stealth Swarm (Plan v6.0)

> **Document Location:** `plan/SEARCH_GAP_RADAR_SWARM_PLAN.md`
> **Last Updated:** 2026-11-12
> **Core Mission:** Discover, evaluate, and monetize high-demand, low-competition search voids across **ANY audience or industry** — Utilities, Calculators, Finance, Legal, Health, B2B, Lifestyle, Developer Tools, and beyond.
> **Budget Constraint:** **$0.00 Hard Rule** — Zero paid APIs, zero paid hosting, zero paid proxies.
> **Guiding Principle:** Broad Macro Root Terms in Trends (`today 12-m`) → 400 organic long-tail queries per batch → Free SERP Sieve → Composite Scoring → 4 Actionable Archetypes.

---

## Table of Contents

1. [The Macro-to-Micro Funnel Philosophy](#1-the-macro-to-micro-funnel-philosophy)
2. [Universal Audience Taxonomy — 12 High-Yield Verticals](#2-universal-audience-taxonomy--12-high-yield-verticals)
3. [Root Niche Sources — 7 Free Automated Pipelines](#3-root-niche-sources--7-free-automated-pipelines)
4. [Stealth Swarm & 12-Cookie Rotation Pool](#4-stealth-swarm--12-cookie-rotation-pool)
5. [Anti-Waste State Machine & Frontier Queue](#5-anti-waste-state-machine--frontier-queue)
6. [Universal Deliverable Archetypes](#6-universal-deliverable-archetypes)
7. [Scoring Engine — Mathematical Specification](#7-scoring-engine--mathematical-specification)
8. [Next-Gen Dashboard UI/UX Specification](#8-next-gen-dashboard-uiux-specification)
9. [Complete File & Code Contracts](#9-complete-file--code-contracts)
10. [Phased Implementation Roadmap](#10-phased-implementation-roadmap)
11. [Known Bugs & Gotchas Fixed](#11-known-bugs--gotchas-fixed)

---

## 1. The Macro-to-Micro Funnel Philosophy

### Why Broad Root Terms Beat Long-Tail Querying in Trends

1. **The Volume Problem:** Querying obscure 5-word phrases directly on Trends often returns *"Not enough search volume."* Root anchors never have this issue.
2. **The Discovery Goldmine:** A broad root term (e.g. `calculator`, `converter`, `visa`, `invoice`, `docker`) triggers Google's real organic search graph:
   - **Top 25 Queries** — What the global market consistently searches over the past 12 months.
   - **Rising Breakouts** — Surging pain points with no content supply, flagged `+5,000%` or `Breakout`.
3. **8× Request Efficiency:**

   > 8 root terms × 25 related queries × 2 (Top + Rising) = **400 raw organic queries per single request**

   A 4-shard GitHub swarm can extract **10,000+ real queries in under 5 minutes** without rate limits.

### The Funnel

```
Broad Root Term (Depth 0)
   └─ Trends Batch → 400 organic queries
         └─ Exclusion Shield (drops noise)
               └─ SERP Sieve (DuckDuckGo, title void check)
                     └─ Dev/Community Evidence (SO, GitHub, HN)
                           └─ Composite Score 0–100
                                 └─ Qualified Gap (≥65) → Archetype mapping → DB
                                       └─ Promising sub-terms → queue as Depth 1 niches
```

### Timeframe Lock

**All Trends queries use `today 12-m`** — past 12 months, web platform. This filters out:
- 7-day hype cycles that disappear in a week.
- Seasonal spikes with no sustained demand.
- Ephemeral news events.

What remains is **evergreen, sustained demand** — the only kind worth building for.

---

## 2. Universal Audience Taxonomy — 12 High-Yield Verticals

The system is **not restricted to developer tools**. Any vertical with evergreen search demand is a valid target. The vertical field on each opportunity drives UI filtering and niche seeding strategy.

| # | Vertical | High-Yield Macro Root Term Examples | Monetizable Deliverable Models |
|---|---|---|---|
| 1 | **Finance & Wealth** | `loan calculator`, `tax calculator`, `mortgage`, `salary after tax`, `roi calculator`, `crypto tax`, `compound interest`, `car payment` | Ad-supported or affiliate finance calculators (CPC: $5–$50). |
| 2 | **Small Business & B2B** | `invoice generator`, `receipt maker`, `contract template`, `bill of sale`, `nda generator`, `profit margin`, `paystub generator` | Single-page PDF generator utilities with pro exports. |
| 3 | **Productivity & Work** | `budget template`, `timesheet`, `habit tracker`, `meeting notes`, `cron generator`, `markdown editor`, `pomodoro timer` | Notion templates, Google Sheets, lightweight web tools. |
| 4 | **Media & File Converters** | `heic to jpg`, `mp4 to gif`, `pdf to word`, `compress png`, `webp converter`, `audio extractor`, `svg to png`, `watermark remover` | Client-side WebAssembly browser utilities (zero server cost). |
| 5 | **Health & Fitness** | `calorie calculator`, `macro calculator`, `bmi chart`, `running pace`, `tdee calculator`, `water intake`, `intermittent fasting` | Mobile-friendly health calculators with newsletter capture. |
| 6 | **Real Estate & Living** | `rent vs buy`, `closing cost calculator`, `square footage`, `moving checklist`, `lease agreement`, `sublet agreement` | Lead-gen widgets for real estate brokers and moving services. |
| 7 | **Legal & Compliance** | `privacy policy generator`, `terms of service template`, `cookie consent banner`, `power of attorney`, `llc operating agreement` | Automated legal document builders and compliance checklists. |
| 8 | **Academic & Education** | `gpa calculator`, `citation generator`, `word count`, `grade calculator`, `percentage increase`, `scientific notation` | Student tools with heavy organic traffic and backlink potential. |
| 9 | **Developer & Cloud** | `docker compose`, `fastapi`, `supabase`, `jwt refresh token`, `ollama`, `kubernetes yaml`, `sql query builder`, `regex tester` | Developer boilerplates, starter kits, troubleshooting recipes. |
| 10 | **Gaming & Entertainment** | `damage calculator`, `stat calculator`, `tier list maker`, `wordle solver`, `pokemon weakness`, `sensitivity converter` | Community utility sites with programmatic SEO. |
| 11 | **E-Commerce & Selling** | `etsy fee calculator`, `ebay fee calculator`, `shopify margin`, `amazon fba fees`, `shipping calculator`, `barcode generator` | Seller tools with affiliate tie-ins to bookkeeping/inventory software. |
| 12 | **Travel & Visas** | `visa requirements for`, `schengen 90 180 calculator`, `flight compensation`, `currency converter`, `packing checklist` | Travel calculators and visa requirement trackers with travel affiliate revenue. |

---

## 3. Root Niche Sources — 7 Free Automated Pipelines

The `engines/niche_ingestor.py` module harvests broad root terms continuously from these zero-cost sources, feeding the `frontier_niches` queue without any human hardcoding.

### Source 1: Google Trends Native Category Taxonomy
- **API:** `GET https://trends.google.com/trends/api/explore?cat=<ID>&hl=en-US`
- **Category IDs to target:** `7` (Finance), `45` (Health), `67` (Real Estate), `18` (Shopping), `5` (Computers), `16` (Games), `11` (Business), `174` (Travel), `71` (Autos), `22` (Law)
- **Output:** Top related queries per category → queue as Depth 0 niches in appropriate verticals.
- **Volume:** ~100–200 root anchors per category × 10 categories = 1,000–2,000 fresh root terms.

### Source 2: Wikipedia Universal Classification Tree
- **API:** `GET https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:<X>&cmlimit=500&format=json`
- **Categories to traverse:**
  - `Category:Calculators`, `Category:Unit_converters`, `Category:Finance_calculators`
  - `Category:Business_software`, `Category:Productivity_software`
  - `Category:Legal_documents`, `Category:Tax_forms`
  - `Category:Health_promotion`, `Category:Fitness_tools`
- **Output:** Article titles → clean and queue as root niche terms.
- **Volume:** 500–3,000 structured concept names per category.

### Source 3: Wikidata Structured Entity Taxonomy
- **API:** Wikidata SPARQL endpoint `https://query.wikidata.org/sparql`
- **Queries to run:**
  - All subclasses of `Q1057954` (financial instrument), `Q11028` (document type), `Q2996394` (measurement unit)
  - All software tools with Wikipedia articles and English labels
- **Output:** English labels → queue as root niches.

### Source 4: Curated "Awesome" Repositories
- **Sources (raw GitHub markdown):**
  - `sindresorhus/awesome` — master list of all awesome lists
  - `awesome-selfhosted/awesome-selfhosted` — web utilities
  - `vinta/awesome-python` — Python tools
  - `enaqx/awesome-react` — React ecosystem
  - `avelino/awesome-go` — Go tools
- **Parser:** Extract `##` section headers and tool names from markdown links `[tool name](url)`.
- **Output:** Tool names queued as Developer & Cloud niche roots.

### Source 5: Stack Overflow Popular Tags
- **API:** `GET https://api.stackexchange.com/2.3/tags?order=desc&sort=popular&site=stackoverflow&pagesize=100&page=<N>`
- **Target:** Top 1,000 tags by question count.
- **Output:** Each tag → Developer & Cloud niche root term.
- **Note:** Response is gzip-compressed; use `gzip.decompress()`.

### Source 6: PyPI & npm Top Packages
- **PyPI:** `GET https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json`
  - Extract `rows[].project` for top 500 packages.
- **npm:** `GET https://registry.npmjs.org/-/v1/search?text=&size=250&from=0`
  - Extract `objects[].package.name` and `objects[].package.description`.
- **Output:** Package names → Developer & Cloud niche roots.

### Source 7: Government & Bureaucracy Document Taxonomies
- **Sources:**
  - IRS Forms index: `https://www.irs.gov/forms-instructions` (HTML parse)
  - USCIS Form catalog: `https://www.uscis.gov/forms/all-forms` (HTML parse)
  - EU Official Documents taxonomy (EUR-Lex)
- **Output:** Form names, visa types, compliance document names → Legal & Travel vertical roots.

### Ingestor Deduplication
- Before queuing any term, compute `hashlib.sha256(term.lower().strip())` and check `explored_signatures` table.
- If signature exists and `explored_at > now - 90 days`, skip.
- Otherwise insert into `frontier_niches` with appropriate `category` and `depth_level = 0`.

---

## 4. Stealth Swarm & 12-Cookie Rotation Pool

### The isdownnow.com Pattern

The same cookie rotation design proven in the `isdownnow.com` project is used here.

#### Cookie Storage

**Local (macOS dev):** `config/cookies.json` — strictly gitignored.

```json
[
  { "id": 1, "cookie": "__Secure-3PSID=...; SID=...; HSID=...; APISID=...; SAPISID=..." },
  { "id": 2, "cookie": "__Secure-3PSID=...; SID=...; HSID=..." },
  ...
  { "id": 12, "cookie": "__Secure-3PSID=...; SID=...; HSID=..." }
]
```

**GitHub Actions:** `TRENDS_COOKIE_POOL` repository secret — same JSON array, base64-encoded or raw.

#### Cookie Loading Logic (`engines/trends_batch.py`)

```python
def load_cookie_pool() -> list[str]:
    # 1. Try local file first
    local_path = os.path.join(BASE_DIR, "config", "cookies.json")
    if os.path.exists(local_path):
        with open(local_path) as f:
            pool = json.load(f)
            return [entry["cookie"] for entry in pool]
    # 2. Fall back to GitHub Actions secret
    raw = os.getenv("TRENDS_COOKIE_POOL", "")
    if raw:
        pool = json.loads(raw)
        return [entry["cookie"] for entry in pool]
    return []  # Anonymous fallback — lower rate limits

def select_cookie(shard_id: int, pool: list[str]) -> str | None:
    if not pool:
        return None
    return pool[shard_id % len(pool)]
```

#### Cookie Injection into Requests

```python
headers = { "User-Agent": random.choice(USER_AGENTS), ... }
cookie = select_cookie(shard_id, load_cookie_pool())
if cookie:
    headers["Cookie"] = cookie
```

### Stealth & Camouflage

| Element | Camouflage Strategy |
|---|---|
| Workflow filename | `.github/workflows/telemetry.yml` |
| Workflow name | `Ecosystem Telemetry & Matrix Dependency Audit` |
| Job name | `verify-integration-vectors` |
| Step names | `Verify ecosystem integration vectors`, `Sync telemetry artifacts` |
| Commit messages | `chore(ci): sync ecosystem telemetry shard-${{ matrix.shard_id }} [skip ci]` |
| DB artifact name | `ecosystem-telemetry-matrix-${{ matrix.shard_id }}` |

### Anti-Fingerprinting

- **User-Agents:** Rotate across 6+ modern Chrome/Safari/Edge UA strings.
- **Jitter:** `random.uniform(2.5, 6.5)` seconds between batch requests.
- **Term order:** `random.shuffle(batch)` before submission.
- **Geo:** Default `geo=""` (global); can be parameterized per shard.
- **Timeframe:** Always `today 12-m` (consistent, non-suspicious).

---

## 5. Anti-Waste State Machine & Frontier Queue

### Why This Exists

Google Trends rate-limits aggressively if the same terms are re-queried too soon. This state machine guarantees:
- No term is ever queried twice within 90 days.
- Parallel shards never duplicate each other's work.
- The discovery queue auto-grows via recursive sub-niche seeding.

### Database Tables to Add (`storage/db.py`)

#### `frontier_niches` — The Discovery Queue

```sql
CREATE TABLE IF NOT EXISTS frontier_niches (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    niche_term        TEXT UNIQUE NOT NULL,
    category          TEXT NOT NULL,          -- One of the 12 verticals
    parent_niche      TEXT DEFAULT NULL,       -- Parent root term (NULL for depth 0)
    depth_level       INTEGER DEFAULT 0,       -- 0=root, 1=sub-niche, 2=micro, 3=ultra-micro
    status            TEXT DEFAULT 'pending',  -- 'pending', 'claimed', 'completed', 'failed'
    queries_extracted INTEGER DEFAULT 0,       -- How many sub-queries were found
    claimed_by_shard  TEXT DEFAULT NULL,       -- Shard ID that claimed this niche
    last_explored_at  TIMESTAMP DEFAULT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier_niches(status, depth_level);
CREATE INDEX IF NOT EXISTS idx_frontier_category ON frontier_niches(category);
```

#### `explored_signatures` — The 90-Day Memory

```sql
CREATE TABLE IF NOT EXISTS explored_signatures (
    signature_hash TEXT PRIMARY KEY,           -- SHA-256 of normalized term
    normalized_term TEXT NOT NULL,
    explored_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Helper Functions to Add (`storage/db.py`)

```python
def claim_frontier_batch(shard_id: int, total_shards: int, batch_size: int = 8) -> list[str]:
    """Atomically claims a batch of pending niches for a specific shard."""
    # SELECT WHERE id % total_shards = shard_id AND status = 'pending'
    # ORDER BY depth_level ASC, created_at ASC
    # LIMIT batch_size
    # UPDATE status='claimed', claimed_by_shard=shard_id

def mark_frontier_complete(niche_term: str, queries_extracted: int) -> None:
    """Marks a niche as completed after successful extraction."""
    # UPDATE status='completed', queries_extracted=N, last_explored_at=NOW

def queue_sub_niche(term: str, category: str, parent: str, depth: int) -> bool:
    """Inserts a discovered sub-term as a new Depth N+1 niche (capped at depth 3)."""
    # Only insert if NOT in explored_signatures AND depth <= 3
    # INSERT OR IGNORE INTO frontier_niches

def is_signature_explored(term: str) -> bool:
    """Returns True if this term was explored within the last 90 days."""
    # hash = sha256(term.lower().strip())
    # SELECT explored_at WHERE signature_hash = hash AND explored_at > NOW - 90 days

def add_signature(term: str) -> None:
    """Records a term as explored today."""
    # INSERT OR REPLACE INTO explored_signatures

def get_frontier_stats() -> dict:
    """Returns pending/claimed/completed/cooldown counts per category."""

def get_frontier_page(status: str, page: int, limit: int) -> tuple[list, int]:
    """Paginated list of frontier niches for the UI explorer."""
```

### Atomic Shard Claiming Logic

```sql
-- Shard 0 of 4 claims:
SELECT * FROM frontier_niches
WHERE status = 'pending' AND id % 4 = 0
ORDER BY depth_level ASC, created_at ASC
LIMIT 8;
```

This guarantees zero overlap between parallel GitHub Actions matrix runners.

### Depth Cap & Recursive Expansion

- **Depth 0:** Broad root (e.g. `calculator`)
- **Depth 1:** Sub-niche (e.g. `loan calculator`, `mortgage calculator`)
- **Depth 2:** Micro-niche (e.g. `loan calculator with extra payments`, `closing cost calculator ontario`)
- **Depth 3:** Ultra-micro — final layer, never expands further
- Promising sub-terms identified during extraction (score ≥ 50 but query is itself a broad concept) are automatically queued as Depth N+1.

---

## 6. Universal Deliverable Archetypes

Every qualified opportunity (Gap Score ≥ 65) is mapped to one of **4 actionable product models** by `engines/scorer.py`:

### Archetype 1: Micro-Tools & Web Utilities
**Signal keywords:** `calculator`, `converter`, `generator`, `tool`, `maker`, `builder`, `formatter`, `tester`, `checker`, `visualizer`
**Examples:** `closing cost calculator ontario`, `heic to pdf converter`, `etsy profit margin calculator`, `cron schedule visualizer`
**Deliverable:** Single-page responsive web app. Stack: static HTML + Alpine.js / Next.js + Tailwind. Hosted on Cloudflare Pages or Vercel (free tier). Zero login required. Programmatic SEO via `<title>` and schema markup.

### Archetype 2: Workarounds & Troubleshooters
**Signal keywords:** `fix`, `error`, `failed`, `issue`, `problem`, `workaround`, `bypass`, `how to`, `not working`, `crash`
**Examples:** `ollama cuda out of memory fix`, `how to cancel adobe subscription without fee`, `cors error local development`
**Deliverable:** Definitive minimal step-by-step resolution guide. Format: Markdown blog or static HTML page. Copy-paste code snippets. Structured FAQ schema markup for rich results.

### Archetype 3: Templates, Checklists & Cheatsheets
**Signal keywords:** `template`, `checklist`, `cheatsheet`, `boilerplate`, `example`, `sample`, `script`, `starter`
**Examples:** `commercial lease agreement template word`, `docker compose postgres pgvector template`, `quarterly estimated tax checklist`
**Deliverable:** Downloadable Google Sheets / Notion template, GitHub starter repo, or printable PDF reference. Gated behind email capture for lead gen.

### Archetype 4: Comparison & Alternative Directories
**Signal keywords:** `vs`, `versus`, `alternative`, `open source`, `free alternative`, `difference between`, `compare`
**Examples:** `victoria metrics vs prometheus`, `free alternatives to quickbooks`, `open source docusign`, `difference between langchain and langgraph`
**Deliverable:** Programmatic comparison directory page. Compares pricing, features, self-hosted options. Schema: `Product`, `ItemList`. Updated programmatically from public data.

---

## 7. Scoring Engine — Mathematical Specification

The composite 0–100 score is calculated in `engines/scorer.py`:

```
Gap Score = SERP Score (0–40) + Dev/Community Score (0–30) + Velocity Score (0–30)
```

### SERP Score (0–40) — `engines/serp_sieve.py`

| Signal | Points |
|---|---|
| Zero exact `<title>` matches in top 10 results | +20 |
| 1–2 exact `<title>` matches | +10 |
| Homepage (root domain) in top 5 for a 4+ word query | +8 (competitor is weak) |
| Forum/Reddit/Quora/Medium in top 3 | +7 (content void) |
| Average result age > 2 years | +5 |

> **Title void** = no result's `<title>` tag matches the query verbatim. The more voids, the less competition.

### Dev/Community Score (0–30) — `engines/dev_evidence.py`

| Signal | Points |
|---|---|
| ≥5 Stack Overflow unresolved questions (accepted_answer_id = null) | +10 |
| 1–4 unresolved SO questions | +5 |
| GitHub: open issues > repos ratio > 3:1 | +10 |
| GitHub: < 3 repos exist for this term | +5 |
| Hacker News: ≥2 Ask HN / Show HN posts | +5 |
| Hacker News: ≥1 discussion thread with comments | +5 |

> For non-developer verticals (Finance, Health, Legal, etc.), substitute: Reddit thread count, Quora question count, Google autocomplete depth.

### Velocity Score (0–30) — from Trends data

| Trend Signal | Points |
|---|---|
| `Breakout` (>5,000%) in Rising queries | +30 |
| Rising query value > 1,000% | +20 |
| Rising query value 200–999% | +12 |
| Top query (stable high volume) | +8 |

### Archetype Classification Logic

```python
def classify_archetype(keyword: str, serp_data: dict) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ["calculator","converter","generator","tool","maker","builder","tester","checker"]):
        return "Micro-Tool"
    if any(w in kw for w in ["fix","error","failed","issue","problem","workaround","bypass","not working","crash"]):
        return "Workaround"
    if any(w in kw for w in ["template","checklist","cheatsheet","boilerplate","example","sample","starter"]):
        return "Template"
    if any(w in kw for w in [" vs "," versus ","alternative","open source","free alternative","difference between","compare"]):
        return "Comparison"
    # Fallback: infer from SERP content types
    return "Micro-Tool"  # Default to most monetizable
```

---

## 8. Next-Gen Dashboard UI/UX Specification

**Tech stack:** FastAPI backend + Tailwind CSS CDN + Alpine.js CDN + Marked.js CDN. No npm build steps, no bundlers. Everything loads from CDN links in `<head>`.

**URL:** `http://localhost:8080` and LAN `http://192.168.100.75:8080`

### Layout Overview

```
┌─────────────────────────────────────────────────────────────┐
│  🪙 GOLD MINER        [Status Pulse] [Run Scan ▶]          │
│  KPI Strip: [💎 23] [⚡ 87] [✅ 4] [🌐 1,240 frontier]     │
│  Vertical Pills: [All] [Finance] [B2B] [Health] ... (12)   │
├─────────────────────────────────────────────────────────────┤
│  [Radar Feed] [Frontier Queue] [Data Table] [Reports] [Admin]│
├─────────────────────────────────────────────────────────────┤
│                     TAB CONTENT                             │
└─────────────────────────────────────────────────────────────┘
```

### Module 1: Command Ribbon & KPI Strip

**Live Status Indicator:**
- 🟢 Pulsing green dot = Swarm Active (GitHub Actions running)
- 🟡 Yellow = Local Daemon Running
- ⚫ Grey = Idle

**KPI Metrics (auto-refresh every 4s):**
- `💎 N` — Critical Gold Mines (score ≥ 85)
- `⚡ N` — High Opportunity (score 65–84)
- `✅ N` — Human Confirmed Gold
- `🌐 N frontier` — Total root terms in discovery queue (pending + completed)
- `📋 N cooldown` — Niches locked in 90-day cooldown

**Global Vertical Filter Pills** (above all tabs):
`[All]` `[Finance]` `[B2B]` `[Productivity]` `[Media]` `[Health]` `[Real Estate]` `[Legal]` `[Education]` `[Developer]` `[Gaming]` `[E-Commerce]` `[Travel]`

Clicking any pill filters ALL tabs simultaneously.

---

### Module 2: Radar Feed (Tab 1)

**View Mode Toggle:** `[🃏 Cards]` / `[☰ Compact]`

#### Card View

Each card contains:

```
┌──────────────────────────────────────────────────────┐
│ [💎 92] 🔥 BREAKOUT +5,000%        [🛠️ Micro-Tool]   │
│                                    [Finance]          │
│ closing cost calculator ontario                       │
│                                                       │
│ Title Void Meter: ████░░░░░░  2/10 (Vulnerable)       │
│ SERP Flags: 🏠 Homepage ranks #3 · 📢 Reddit #1       │
│                                                       │
│ 📊 SO: 7 unresolved · GH: 2 repos · HN: 3 posts      │
│                                                       │
│ [🔍 Google ↗] [🦆 DuckDuckGo ↗] [📈 Trends 12m ↗]   │
│                                                       │
│ [💎 Confirm Gold] [❌ Reject] [⏳ Snooze] [🤖 Blueprint]│
└──────────────────────────────────────────────────────┘
```

**Score pill colors:**
- ≥ 85 → Amber/Gold gradient
- 65–84 → Emerald green gradient
- 40–64 → Slate/blue
- < 40 → Dimmed grey (hidden by default unless filter set to show all)

**Velocity badge:**
- `🔥 BREAKOUT +5,000%` — Trends `isBreakout = true`
- `⚡ RISING +N%` — Rising query with specific percentage
- `🟢 STABLE` — Top query with consistent volume

**Title Void Meter:**
- Visual bar: `exact_title_matches / 10`
- Label: `0/10 Untouched Void 🛡️` / `1–2/10 Vulnerable` / `3–5/10 Competitive` / `6+/10 Saturated`

**3-Click Verification Links:**
- Google: `https://www.google.com/search?q=<url-encoded-keyword>`
- DuckDuckGo: `https://duckduckgo.com/?q=<url-encoded-keyword>`
- Trends 12m: `https://trends.google.com/trends/explore?q=<encoded>&date=today%2012-m`

**1-Click AI Blueprint Button (`[🤖 Blueprint]`):**
Opens a modal with copy-paste ready product spec:
```
🏗️ BUILDER BLUEPRINT: "closing cost calculator ontario"
Archetype: Micro-Tool
Target Audience: Canadian homebuyers
Recommended Stack: Static HTML + Alpine.js + Cloudflare Pages
SEO Title: "Closing Cost Calculator Ontario 2025 — Free Instant Estimate"
Meta Description: "Calculate your Ontario closing costs instantly. Includes land transfer tax, legal fees, title insurance and more. Free, no signup."
H1: "Ontario Closing Cost Calculator"
Implementation Prompt: "Build a single-page closing cost calculator for Ontario, Canada. Include: land transfer tax (using official ON brackets), legal fees ($1,500 flat), title insurance ($300 flat), home inspection ($500 flat). Input: purchase price slider ($100k–$2M). Output: itemized cost table + grand total. Use Alpine.js for reactivity. No backend. Dark mode support."
Keyword Variants to Target: ["ontario closing cost calculator", "closing costs ontario", "land transfer tax ontario calculator"]
Monetization: Google AdSense (high CPC real estate ads)
```

#### Compact View

Dense table row:
```
[92] 🔥  closing cost calculator ontario  [Finance][Micro-Tool]  [💎][❌][⏳]  [G↗][D↗][T↗]
```

**Feed Controls:**
- Min score filter slider (0 → 100)
- Sort: `Score ↓` / `Date Added ↓` / `Velocity ↓`
- Verdict filter: `All` / `Pending` / `Confirmed` / `Rejected` / `Snoozed`
- Pagination: 20 per page, `← Prev` / `Next →`

---

### Module 3: Frontier Queue Explorer (Tab 2)

**Purpose:** See and manage the discovery queue — what root terms are pending, being processed, or done.

**Queue Stats Bar:**
```
[🟡 Pending: 1,240]  [🔵 Claimed: 32]  [✅ Completed: 580]  [⏰ Cooldown: 310]
```

**Hierarchy Tree:**
```
▼ Finance (Depth 0)
   ├─ ✅ loan calculator → 42 sub-queries found
   ├─ 🟡 mortgage calculator → pending
   └─ 🔵 tax calculator → claimed by shard-2
      ├─ ✅ federal tax calculator (Depth 1)
      └─ 🟡 state income tax calculator (Depth 1)
```

**Add Seed Term Form:**
```
[ Enter root term... ] [ Select Vertical ▼ ] [ + Add to Queue ]
```

Calls `POST /api/frontier/add` to inject new root terms on the fly.

**Filter options:** By vertical, by status, by depth level.

---

### Module 4: Data Table Explorer (Tab 3)

**Features:**
- Full-text search (instant client-side filter)
- Sortable columns: Score, Keyword, Category, Archetype, Verdict, Date
- Checkbox multi-select per row
- **Bulk Actions:** `Bulk Confirm Gold` / `Bulk Reject` / `Bulk Export Selected`
- **Export Formats:** CSV / JSON / Markdown Checklist

**Markdown export format:**
```markdown
# Gold Mine Action Checklist — 2026-11-12
## 💎 Critical (Score ≥ 85)
- [ ] closing cost calculator ontario [Micro-Tool] — Score: 92
- [ ] heic to pdf free online [Micro-Tool] — Score: 88
## ⚡ High Opportunity (Score 65–84)
- [ ] docker compose postgres pgvector [Template] — Score: 78
```

---

### Module 5: Daily Briefs & Spec Reader (Tab 4)

- Renders `/reports/*.md` via Marked.js (CDN, no build).
- Date navigation: dropdown list of all report files.
- Code blocks: syntax-highlighted via Prism.js CDN.
- Copy button on all code blocks.

---

### Module 6: Swarm Telemetry & Live Terminal (Tab 5 — Admin)

**Controls:**
- `[▶ Run Scan Now]` button — triggers background pipeline scan
- Scan category selector (All or specific vertical)
- Batch depth limit (1 = one batch per category)

**4-Shard GitHub Actions Status:**
```
Shard 0: ✅ Last run: 2h ago  | 42 queries found | 3 gold
Shard 1: 🟡 Running…         | 17 queries found
Shard 2: ✅ Last run: 2h ago  | 38 queries found | 1 gold
Shard 3: ⚫ Idle
```

**12-Cookie Health Bar:**
```
Cookie 1  [🟢 Active]  Cookie 2  [🟢 Active]  ...  Cookie 12 [🔴 Expired]
```

**Live Terminal Log (streaming):**
- Filter tabs: `ALL` / `💎 GOLD` / `SERP` / `❌ ERRORS`
- Auto-scroll toggle
- Last 200 log lines from `/api/logs`

---

## 9. Complete File & Code Contracts

### Directory Structure

```
Gold Miner/
├── plan/
│   └── SEARCH_GAP_RADAR_SWARM_PLAN.md         ← this file
├── engines/
│   ├── trends_batch.py                          ← HTTP Trends extractor (cookie-aware)
│   ├── trends_batch.js                          ← Playwright version for GH Actions
│   ├── exclusion_shield.py                      ← Query noise filter
│   ├── serp_sieve.py                            ← DuckDuckGo SERP auditor
│   ├── dev_evidence.py                          ← SO + GitHub + HN signals
│   ├── scorer.py                                ← 0–100 composite scoring
│   ├── niche_ingestor.py                        ← [TO BUILD] 7-source root harvester
│   └── swarm_worker.py                          ← [TO BUILD] Shard runner CLI
├── storage/
│   ├── db.py                                    ← SQLite layer (needs frontier tables)
│   └── niche_gaps.db                            ← SQLite WAL database
├── config/
│   ├── dev_niches.json                          ← Legacy seed (superseded by ingestor)
│   └── cookies.json                             ← 🔒 GITIGNORED — 12 Google cookies
├── ui/
│   ├── templates/index.html                     ← [TO REDESIGN] Dashboard HTML
│   └── static/app.js                            ← [TO EXTEND] Alpine.js app
├── reports/                                     ← Daily markdown briefs (auto-generated)
├── .github/workflows/
│   ├── radar.yml                                ← Existing basic workflow (keep)
│   └── telemetry.yml                            ← [TO BUILD] Stealth 4-shard workflow
├── dashboard.py                                 ← FastAPI server (needs new endpoints)
├── radar_daemon.py                              ← 24/7 background worker
├── run_dashboard.sh                             ← 1-click dashboard launcher
├── run_radar.sh                                 ← 1-click radar launcher
├── requirements.txt                             ← Python deps
├── package.json                                 ← Node deps (playwright for CI)
├── .env.example                                 ← Documents GITHUB_TOKEN, STACKAPPS_KEY
└── .gitignore                                   ← Excludes cookies.json, .env, *.db-shm
```

---

### `storage/db.py` — New Functions Required

```python
# Frontier queue management
claim_frontier_batch(shard_id, total_shards, batch_size=8) -> list[str]
mark_frontier_complete(niche_term, queries_extracted) -> None
queue_sub_niche(term, category, parent, depth) -> bool
is_signature_explored(term) -> bool
add_signature(term) -> None
get_frontier_stats() -> dict  # {pending, claimed, completed, cooldown, by_category}
get_frontier_page(status, page, limit) -> tuple[list, int]

# Verdict extension
update_verdict(query_id, verdict)  # Add 'snoozed' as valid verdict alongside existing
```

---

### `engines/niche_ingestor.py` — Full Contract

```python
"""
Universal Root Niche Harvester
Populates frontier_niches from 7 free automated sources.
Run standalone: python3 engines/niche_ingestor.py [--source all|so|pypi|npm|wiki|trends|gov]
"""

class NicheIngestor:
    def run_all(self) -> dict  # {source: count_queued}
    def ingest_stackoverflow_tags(self, pages=10) -> int
    def ingest_pypi_packages(self, top_n=500) -> int
    def ingest_npm_packages(self, pages=5) -> int
    def ingest_wikipedia_categories(self) -> int
    def ingest_wikidata_entities(self) -> int
    def ingest_awesome_lists(self) -> int
    def ingest_trends_categories(self) -> int
    def ingest_government_docs(self) -> int
    def _queue_term(self, term, category, source) -> bool  # Checks sig + inserts
```

---

### `engines/swarm_worker.py` — Full Contract

```python
"""
Swarm Shard Runner
Run: python3 -m engines.swarm_worker --shard-id 0 --total-shards 4 [--dry-run]

Loop:
1. claim_frontier_batch(shard_id, total_shards) → list of niche terms
2. For each batch of 8 terms:
   a. TrendsBatchHTTP.extract_batch(terms, cookie=select_cookie(shard_id))
   b. For each returned query:
      - ExclusionShield.should_drop() → skip if dropped
      - SerpSieve.audit() → serp_score
      - DevEvidenceCollector.collect() → dev_score
      - compute_composite_score() → gap_score, archetype
      - upsert_query() if gap_score >= 40
      - If gap_score >= 50 and query looks like a broad root → queue_sub_niche(depth+1)
   c. add_signature(niche_term)
   d. mark_frontier_complete(niche_term, len(found_queries))
   e. Random jitter 2.5–6.5s between batches
3. Generate/update daily report
4. Git commit + push (GitHub Actions context)
"""
```

---

### `dashboard.py` — New API Endpoints Required

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/frontier` | Paginated frontier_niches. Params: `status`, `page`, `limit`, `category` |
| `GET` | `/api/frontier/stats` | Queue telemetry: pending/claimed/completed/cooldown counts |
| `POST` | `/api/frontier/add` | Body: `{term, category}`. Adds new seed root term to queue. |
| `POST` | `/api/bulk-verdict` | Body: `{ids: [int], verdict: str}`. Bulk update verdicts. |
| `GET` | `/api/cookies/status` | Returns count of loaded cookies and IDs (no actual cookie values). |

---

### `.github/workflows/telemetry.yml` — Full Spec

```yaml
name: Ecosystem Telemetry & Matrix Dependency Audit

on:
  schedule:
    - cron: '0 0,6,12,18 * * *'   # 4× daily: midnight, 6am, noon, 6pm UTC
  workflow_dispatch:               # Manual trigger

jobs:
  verify-integration-vectors:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard_id: [0, 1, 2, 3]
      max-parallel: 4
      fail-fast: false

    steps:
      - name: Checkout ecosystem
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python runtime
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install integration dependencies
        run: pip install -r requirements.txt

      - name: Verify ecosystem integration vectors
        env:
          TRENDS_COOKIE_POOL: ${{ secrets.TRENDS_COOKIE_POOL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          STACKAPPS_KEY: ${{ secrets.STACKAPPS_KEY }}
          SHARD_ID: ${{ matrix.shard_id }}
          TOTAL_SHARDS: 4
        run: |
          python3 -m engines.swarm_worker \
            --shard-id $SHARD_ID \
            --total-shards $TOTAL_SHARDS

      - name: Sync telemetry artifacts
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          git config user.email "ci@ecosystem-telemetry.local"
          git config user.name "Ecosystem Telemetry CI"
          git add storage/niche_gaps.db reports/
          git diff --cached --quiet || \
            git commit -m "chore(ci): sync ecosystem telemetry shard-${{ matrix.shard_id }} [skip ci]"
          git pull --rebase origin main
          git push
```

> **Note on DB sync:** SQLite WAL mode allows concurrent reads. Writes from different shards must be serialized via the `claim_frontier_batch` atomic select+update. The `git pull --rebase` before push ensures the DB file is always up to date — but parallel shard pushes may conflict. Consider using a shard-specific `.json` artifact per shard and merging in a final `consolidate` job, or use `git stash + pull + stash pop` strategy.

---

### `ui/templates/index.html` — Key Structure

```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🪙 Gold Miner — Search Gap Radar</title>
  <!-- CDN: NO build steps -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1/themes/prism-tomorrow.min.css">
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1/components/prism-core.min.js"></script>
</head>
<body class="bg-gray-950 text-gray-100" x-data="radarApp()" x-init="initApp()">
  <!-- Command Ribbon -->
  <!-- Vertical Filter Pills -->
  <!-- Tab Navigation -->
  <!-- Tab: Radar Feed -->
  <!-- Tab: Frontier Queue -->
  <!-- Tab: Data Table -->
  <!-- Tab: Daily Briefs -->
  <!-- Tab: Admin / Swarm Monitor -->
  <!-- AI Blueprint Modal -->
  <script src="/static/app.js"></script>
</body>
</html>
```

---

### `ui/static/app.js` — New Functions Required

```javascript
// Frontier queue
async loadFrontierStats()           // GET /api/frontier/stats
async loadFrontierQueue(page)       // GET /api/frontier?page=N
async addSeedTerm(term, category)   // POST /api/frontier/add

// Bulk operations
async bulkVerdict(ids, verdict)     // POST /api/bulk-verdict
toggleSelectAll()                   // checkbox select-all in table view
toggleSelect(id)                    // checkbox toggle for single row
exportSelected(format)              // CSV/JSON/Markdown of selected rows

// Blueprint generator
generateBlueprint(item)             // Returns blueprint object from item data
openBlueprintModal(item)            // Opens modal with blueprint content
copyBlueprint()                     // Clipboard copy of blueprint text

// 3-way verify links (URL generators)
googleUrl(keyword)                  // `https://www.google.com/search?q=${encodeURIComponent(keyword)}`
ddgUrl(keyword)                     // `https://duckduckgo.com/?q=${encodeURIComponent(keyword)}`
trendsUrl(keyword)                  // `https://trends.google.com/trends/explore?q=${encodeURIComponent(keyword)}&date=today%2012-m`

// Verdict extension
async setVerdict(id, verdict)       // 'confirmed_gold' | 'already_served' | 'pending' | 'snoozed'

// Cookie status
async loadCookieStatus()            // GET /api/cookies/status
```

---

## 10. Phased Implementation Roadmap

| Phase | Priority | Milestone | Key Files | Status |
|---|---|---|---|---|
| **Phase 1** | 🔴 Critical | **DB Schema Upgrade** — Add `frontier_niches`, `explored_signatures` tables + all helper functions | `storage/db.py` | ⬜ TODO |
| **Phase 2** | 🔴 Critical | **Cookie Integration in Trends Engine** — Add `load_cookie_pool()`, `select_cookie()`, inject `Cookie` header; switch default to `today 12-m` | `engines/trends_batch.py` | ⬜ TODO |
| **Phase 3** | 🔴 Critical | **Universal Niche Ingestor** — All 7 sources; calls `queue_sub_niche()` | `engines/niche_ingestor.py` (new) | ⬜ TODO |
| **Phase 4** | 🟠 High | **Swarm Shard Runner** — `--shard-id`, `--total-shards` CLI; full pipeline per shard | `engines/swarm_worker.py` (new) | ⬜ TODO |
| **Phase 5** | 🟠 High | **Stealth GitHub Actions Workflow** — 4-matrix shards, 4× daily, DB push | `.github/workflows/telemetry.yml` (new) | ⬜ TODO |
| **Phase 6** | 🟡 Medium | **New Dashboard API Endpoints** — `/api/frontier*`, `/api/bulk-verdict`, `/api/cookies/status`; `snoozed` verdict | `dashboard.py` | ⬜ TODO |
| **Phase 7** | 🟡 Medium | **Full UI Redesign** — Card/Grid toggle, 12 vertical pills, Frontier tab, Blueprint modal, 3-way verify, bulk ops, cookie health bar | `ui/templates/index.html`, `ui/static/app.js` | ⬜ TODO |
| **Phase 8** | 🟢 Low | **Verdict Extension** — Add `snoozed` verdict in DB; update `update_verdict()` | `storage/db.py` | ⬜ TODO |
| **Phase 9** | 🟢 Low | **Git Remote & GitHub Setup** — Push repo, set `TRENDS_COOKIE_POOL` secret, enable Actions | Manual | ⬜ TODO |
| **Phase 10** | 🟢 Low | **Niche Ingestor Initial Seed Run** — Run ingestor locally to pre-populate 500+ frontier niches before first swarm | `python3 engines/niche_ingestor.py` | ⬜ TODO |

### Recommended Build Order
1. Phase 1 → 2 → 3 → 4 → 5 (core data pipeline — do these together in one session)
2. Phase 6 → 7 (dashboard — do together in one session)
3. Phase 8 → 9 → 10 (polish + deployment)

---

## 11. Known Bugs & Gotchas Fixed

These issues were discovered in the first implementation pass. Any re-implementation must respect these fixes:

| Bug | Root Cause | Fix |
|---|---|---|
| `sqlite3.ProgrammingError: Cannot operate on a closed database` | `conn.close()` inside `with conn:` block | Use `try/finally` pattern. Never call `conn.close()` inside `with conn:` |
| `SSL CERTIFICATE_VERIFY_FAILED` on macOS for all external HTTPS requests | macOS doesn't ship CA certs for Python | Add `SSL_CTX = ssl._create_unverified_context()` and pass `context=SSL_CTX` to every `urlopen()` call |
| `NameError: name 'urllib' is not defined` in `dashboard.py` | `urllib.parse` used in route handler but only `urllib` was imported | Add explicit `import urllib.parse` |
| Stack Exchange API returns empty bytes | Response is gzip-compressed | Wrap with `gzip.decompress(response_bytes)` before `json.loads()` |
| Noise queries passing exclusion shield (pricing, founders, download, laptop, etc.) | Original shield too permissive | Enhanced `EXCLUSION_PATTERNS` list in `engines/exclusion_shield.py`; purge bad DB entries after each enhancement |
| `npx playwright install chromium` interactive prompt hangs in script | npm expects TTY | Use `npx playwright install chromium --with-deps` or pre-install in `package.json` postinstall |
| Google Trends API 429 on unauthenticated requests | No cookie = bot detection | Always inject `Cookie` header when available; fall back gracefully to Google Suggest |
| Parallel shard DB write conflicts | SQLite single-writer constraint | WAL mode helps but atomic `claim_frontier_batch` SELECT+UPDATE prevents double-claiming |
| `today 12-m` vs `now 1-d` — wrong timeframe default | Old code had `now 1-d` hardcoded | Default must be `today 12-m` everywhere. Grep and replace any `now 1-d` occurrences |

---

*Plan v6.0 — ready for single-session full implementation.*
