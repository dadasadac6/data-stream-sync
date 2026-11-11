# Autonomous Niche Swarm & Evergreen Frontier Radar (Plan v4.0)

> **Document Location:** `plan/SEARCH_GAP_RADAR_SWARM_PLAN.md`  
> **Target Execution:** GitHub Actions Stealth Swarms + Local FastAPI Dashboard  
> **Budget Constraint:** **$0.00 Hard Rule** (Zero paid APIs, zero paid hosting, zero paid proxies)  
> **Focus:** 100% Durable, Evergreen Developer Search Gaps (No ephemeral 7-day hype)

---

## 1. Core Architectural Pillars

### Pillar 1: Evergreen Macro Timeframe (`today 12-m`)
* **The Principle:** Ephemeral trends (viral 7-day social media tools, one-off crypto news, temporary cloud outages) are discarded.
* **The Configuration:** All Google Trends requests are pinned to **`today 12-m` (Past 12 Months Web Search)**.
* **The Value:** Yields queries with sustained, year-long volume, recurring developer workflow friction, permanent library migration voids, and evergreen micro-tool opportunities.

---

### Pillar 2: Stealth Swarm Architecture & 12-Cookie Rotation Pool
To query thousands of terms on Google Trends from GitHub Actions without rate limits or bot detection:

1. **Cookie Management & Secret Storage:**
   * **GitHub Actions:** Stored in a GitHub repository secret named `TRENDS_COOKIE_POOL`. It contains a JSON array of the 12 Google login cookies / session cookies (imported from the `isdownnow.com` project):
     ```json
     [
       { "id": 1, "cookie": "__Secure-3PSID=...; SID=...; HSID=..." },
       { "id": 2, "cookie": "__Secure-3PSID=...; SID=...; HSID=..." },
       ...
       { "id": 12, "cookie": "__Secure-3PSID=...; SID=...; HSID=..." }
     ]
     ```
   * **Local / Daemon Environment:** Stored in `config/cookies.json` (strictly added to `.gitignore`), or in `.env` as `GOOGLE_COOKIE_POOL='[...]'`.
   * **Shard Rotation:** Swarm shards rotate through cookies using `shard_id % 12` with automatic round-robin fallback if an individual cookie expires.

2. **Stealth & Obfuscation Measures:**
   * **Camouflaged CI/CD Workflow:** The workflow file `.github/workflows/telemetry.yml` and job names are titled generically as routine project health checks (e.g. `name: "Ecosystem Telemetry & Matrix Dependency Audit"`, `step: "Verify ecosystem integration vectors"`).
   * **Camouflaged Git Commits:** Automated SQLite delta commits use generic messages: `chore(ci): update ecosystem telemetry matrix [skip ci]`.
   * **Anti-Fingerprinting:**
     * Rotates real browser `User-Agent` strings across modern Chrome and Safari on macOS/Windows.
     * Inserts randomized jitter delays (2.5s to 6.5s) between batch requests.
     * Randomized term ordering within batches.

---

### Pillar 3: Research on Sourcing Massive Developer Root Niches

To power continuous expansion without manual hardcoding, the radar taps into **6 massive, free, programmatic sources**:

| Source | Ingestion Mechanism | Yield | Description |
|---|---|---|---|
| **1. Stack Overflow Tags API** | REST API (`/2.3/tags?sort=popular`) | **65,000+** vetted tech tags | Canonical programming languages, frameworks, libraries, databases, and DevOps tools with usage counts. |
| **2. GitHub Curated "Awesome" Lists** | Raw GitHub Markdown parser | **40,000+** categorized libraries | Curated community lists (`sindresorhus/awesome`, `vinta/awesome-python`, `enaqx/awesome-react`, `avelino/awesome-go`, `dhamaniasad/awesome-postgres`, etc.). |
| **3. GitHub Topics API** | GitHub Search API (`/search/topics`) | **50,000+** developer topics | Official GitHub repository topics covering AI, cloud, WebAssembly, security, and mobile. |
| **4. Top Package Registries** | Public registry APIs & BigQuery exports | **25,000+** active packages | Top 2,000 downloaded packages from PyPI, npm (`registry.npmjs.org`), Crates.io (Rust), and Go pkg. |
| **5. CNCF Cloud Native Landscape** | Raw YAML/JSON from `cncf/landscape` | **1,500+** cloud & DevOps tools | Every enterprise cloud, Kubernetes, database, observability, and networking project. |
| **6. Hacker News Algolia Discussions** | Free unmetered Algolia API | Continuous stream | "Ask HN" and "Show HN" developer launch topics with high comment engagement. |

---

### Pillar 4: Dynamic Frontier Graph & Recursive Sub-Niche Breeding

```mermaid
flowchart TD
    ROOT["Root Niche Ingestor<br/>(SO Tags, Awesome Lists, CNCF, PyPI, npm)"]
    Q[("Frontier Queue Table<br/>frontier_niches (SQLite)")]
    SEEN[("Explored Signatures Table<br/>explored_signatures (SQLite)")]

    ROOT -->|Queue Root Seeds (Depth 0)| Q

    subgraph SWARM["GitHub Actions Stealth Swarm (4 Shards)"]
        S1["Shard 1 (AI/LLM)"]
        S2["Shard 2 (Cloud/DevOps)"]
        S3["Shard 3 (Databases/APIs)"]
        S4["Shard 4 (Frameworks/Tools)"]
    end

    Q -->|Claim Unexplored Batches| SWARM
    SEEN -.->|Anti-Duplication Shield| SWARM

    SWARM --> T["Google Trends (12-Cookie Rotation, 'today 12-m')"]
    T --> RAW["Raw Related Queries (Top & Rising)"]

    subgraph PIPELINE["Dual-Evidence Sieve Pipeline"]
        EX["Exclusion Shield (Drops corporate/navigational noise)"]
        SERP["DuckDuckGo HTML SERP Screen (Exact title voids, root leaks)"]
        DEV["Dev Evidence (GitHub Issues vs Repos, Stack Overflow, HN)"]
        SCORE["Scorer (0-100) -> 4 Developable Archetypes"]
        EX --> SERP --> DEV --> SCORE
    end

    RAW --> PIPELINE
    SCORE --> DB[("storage/niche_gaps.db")]
    SCORE -->|Extract Sub-Niches (Depth + 1 <= 3)| Q
    PIPELINE -->|Mark Signature Done| SEEN
```

#### Rules for Recursive Sub-Niche Breeding:
1. **Depth Cap:** Recursive expansion is capped at `depth_level <= 3` to ensure relevance does not drift into broad consumer topics.
2. **Sub-Niche Qualification:** A related query yielded from Trends is promoted into `frontier_niches` if:
   * It contains at least one technical token (`api`, `sdk`, `docker`, `orm`, `hook`, `rag`, `wasm`, `auth`, `cli`, `engine`, `cluster`).
   * It is not already in `explored_signatures`.
   * It has sufficient search interest ($>20\%$ relative interest).
3. **Strict Deduplication:**
   * Before querying, hashes of normalized queries are verified against `explored_signatures`.
   * Even after restarts or multiple daily runs, **the radar will never re-crawl an already analyzed term within 30 days**.

---

## 2. Updated SQLite Database Schema

```sql
-- 1. Dynamic Frontier Queue
CREATE TABLE IF NOT EXISTS frontier_niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niche_term TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    parent_niche TEXT DEFAULT NULL,
    depth_level INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending', -- 'pending', 'claimed', 'completed', 'failed'
    queries_extracted INTEGER DEFAULT 0,
    claimed_by_shard TEXT DEFAULT NULL,
    last_explored_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier_niches(status, depth_level);
CREATE INDEX IF NOT EXISTS idx_frontier_category ON frontier_niches(category);

-- 2. Explored Signatures Anti-Duplication Cache
CREATE TABLE IF NOT EXISTS explored_signatures (
    signature_hash TEXT PRIMARY KEY,
    normalized_term TEXT NOT NULL,
    explored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Core Opportunities Table (Enhanced)
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    source_niche TEXT,
    depth_level INTEGER DEFAULT 0,
    trend_type TEXT NOT NULL,          -- 'BREAKOUT', 'RISING', 'TOP'
    trend_velocity TEXT,               -- e.g. '+3,200%', 'Breakout'
    gap_score INTEGER NOT NULL,        -- 0 to 100
    archetype TEXT NOT NULL,           -- 'Micro-Tool', 'Workaround', 'Recipe', 'Breaking News'
    exact_title_matches INTEGER DEFAULT 0,
    has_github_issues BOOLEAN DEFAULT 0,
    has_stack_questions BOOLEAN DEFAULT 0,
    top_competitor_title TEXT,
    top_competitor_url TEXT,
    human_verdict TEXT DEFAULT 'pending', -- 'confirmed_gold', 'already_served', 'pending'
    evidence_json TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gap_score ON queries(gap_score DESC);
CREATE INDEX IF NOT EXISTS idx_archetype ON queries(archetype);
CREATE INDEX IF NOT EXISTS idx_verdict ON queries(human_verdict);
CREATE INDEX IF NOT EXISTS idx_category ON queries(category);
```

---

## 3. GitHub Actions Stealth Swarm Workflow (`.github/workflows/telemetry.yml`)

```yaml
name: Ecosystem Telemetry & Matrix Dependency Audit

on:
  schedule:
    # Runs 4 times daily (00:00, 06:00, 12:00, 18:00 UTC)
    - cron: '0 0,6,12,18 * * *'
  workflow_dispatch:
    inputs:
      target_depth:
        description: 'Target frontier exploration depth (0-3)'
        required: false
        default: '1'

jobs:
  audit-shard:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    strategy:
      fail-fast: false
      max-parallel: 4
      matrix:
        shard_id: [0, 1, 2, 3]
        total_shards: [4]
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Execute Swarm Shard Sweep
        env:
          SHARD_ID: ${{ matrix.shard_id }}
          TOTAL_SHARDS: ${{ matrix.total_shards }}
          TRENDS_COOKIE_POOL: ${{ secrets.TRENDS_COOKIE_POOL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m engines.swarm_worker --shard-id ${{ matrix.shard_id }} --total-shards ${{ matrix.total_shards }}

      - name: Commit Shard Delta & Sync State
        run: |
          git config --local user.name "github-actions[bot]"
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git pull --rebase origin main || true
          git add storage/niche_gaps.db reports/
          git diff --quiet && git diff --staged --quiet || git commit -m "chore(ci): sync ecosystem telemetry shard-${{ matrix.shard_id }} [skip ci]"
          git push origin main || true
```

---

## 4. Implementation Steps & Milestones

1. **Phase 1: DB Migration & Anti-Duplication Cache**
   * Update `storage/db.py` to create `frontier_niches` and `explored_signatures` tables.
   * Implement atomic batch claiming and signature verification functions.

2. **Phase 2: Multi-Source Root Niche Ingestor (`engines/niche_ingestor.py`)**
   * Build free ingestors for Stack Overflow Top Tags, GitHub Awesome lists, and PyPI/npm top packages to seed thousands of technical root niches automatically.

3. **Phase 3: Cookie Pool & Trends Engine Update (`engines/trends_batch.py`)**
   * Add support for `config/cookies.json` and the `TRENDS_COOKIE_POOL` secret.
   * Lock timeframe parameter to `today 12-m` (Past 12 months) for all requests.
   * Implement automatic round-robin cookie rotation across the 12 sessions.

4. **Phase 4: Swarm Worker & Recursive Sub-Niche Breeder (`engines/swarm_worker.py`)**
   * Implement `swarm_worker.py` taking `--shard-id` and `--total-shards`.
   * Automatically promote qualifying related queries to `frontier_niches` with `depth_level + 1 <= 3`.

5. **Phase 5: Stealth GitHub Actions Workflow (`.github/workflows/telemetry.yml`)**
   * Configure 4-shard matrix execution with obfuscated job names and atomic rebase commits.

6. **Phase 6: Dashboard Frontier Telemetry**
   * Add a "Frontier & Swarm" panel to the dashboard displaying queue size, unvisited niches, depth distribution, and cookie pool health.
