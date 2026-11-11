# Prompt for Antigravity (Copy and paste this into your new chat in 'Gold Miner')

```text
You are an expert full-stack systems and data engineer building the "Autonomous Developer Search Gap Radar" (Gold Miner).

All specifications, architectural blueprints, and engine code are already provided in this workspace:
1. SEARCH_GAP_RADAR_MASTER_PLAN.md (Master architectural blueprint v3.0)
2. GOOGLE_TRENDS_BATCH_EXPLORE_SPEC.md (8-term Google Trends batch comparison engine)
3. SEARCH_GAP_RADAR_v5_FREE_DELTA.md (Zero-cost constraints & developer evidence APIs)
4. bulk_niche_gap_finder.py (Working prototype of free SERP & Google Suggest parser)

### STRICT PROJECT CONSTRAINTS:
- HARD RULE: $0.00 spend. Zero paid APIs, zero paid hosting, zero paid proxies.
- Dual-Runner Portability: Works both locally on macOS and headlessly on GitHub Actions (.github/workflows/radar.yml).
- Pure Data-Driven: Evaluates all raw related queries (Top & Rising Breakouts) returned by Google Trends—no artificial keyword assumptions.
- Exclusion Shield: Auto-drops .gov, .edu, .mil, and brand-owned navigational pages (brand.com/login, etc.).
- Dual-Evidence Sieve: Combines free web SERP checks (exact <title> voids, root-domain leaks) with free official developer APIs (Stack Exchange unresolved questions, GitHub open issues vs repos, Hacker News Algolia).
- Targets 4 Developable Archetypes: Micro-Tools, Detailed Workarounds/Bug Fixes, Developer Recipes/Boilerplates, and Breaking Tech Updates.
- Localhost & LAN Dashboard: FastAPI + Tailwind CSS + Alpine.js served on http://localhost:8080 (and LAN http://192.168.100.75:8080) with 1-click Google search verification links and daily Markdown reports viewer.

### YOUR TASK:
Read SEARCH_GAP_RADAR_MASTER_PLAN.md and GOOGLE_TRENDS_BATCH_EXPLORE_SPEC.md, then implement the complete project end-to-end:

1. Setup Project Skeleton:
   Create all directories: engines/, config/, storage/, reports/, ui/templates/, ui/static/, .github/workflows/
2. Database Layer (storage/db.py):
   Initialize SQLite (storage/niche_gaps.db) with WAL mode, indexing, and deduplication cache.
3. Google Trends 8-Batch Engine (engines/trends_batch.js):
   Implement the 8-term Playwright batch explorer with Blueprint B cloud fallback (%2C delimiter, %2520 space double-encoding, 350-500ms anti-429 jitter).
4. Exclusion Shield & Developer Evidence:
   - engines/exclusion_shield.py: Drops institutional & navigational queries.
   - engines/serp_sieve.py: Free DuckDuckGo HTML SERP auditor (extracts top 10, exact title matches, root-domain leaks).
   - engines/dev_evidence.py: Stack Exchange API + GitHub Search API + Hacker News Algolia collectors.
   - engines/scorer.py: Mathematical scoring (0-100) and mapping to the 4 developable archetypes.
5. Seed Configuration (config/dev_niches.json):
   Curate 8-keyword seed batches across 8 high-yield developer categories (AI/LLM, Cloud/DevOps, Databases, Frameworks, APIs, Auth/Security, Data Tools, Mobile/Cross-platform).
6. Localhost & LAN Dashboard (dashboard.py + ui/templates/index.html):
   FastAPI web app with Tailwind CSS + Alpine.js featuring:
   - Live Gold Mine Feed (filterable cards with velocity badges and 1-click Google search verify link + [Confirm Gold]/[Reject] buttons).
   - Data Table Explorer (exportable to CSV/JSON).
   - Daily Reports Viewer (rendering /reports/*.md specs).
   - Admin Controls (Run Scan Now button, category toggles, live logs).
7. Background Daemon & Automation:
   - radar_daemon.py: Autonomous 24/7 background worker loop.
   - run_dashboard.sh & run_radar.sh: Executable 1-click startup scripts.
   - .github/workflows/radar.yml: Automated GitHub Actions scheduled workflow.

Begin execution immediately with Step 1 and proceed methodically until the complete system is verified, tested, and running!
```
