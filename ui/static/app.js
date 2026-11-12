/**
 * Gold Miner Radar UI Application (Alpine.js State Manager v7.0)
 * Modern Zero-Scroll Workspace:
 * - Two-Pane Niche Radar (Input Keywords Explorer + Discovered Results)
 * - Frontier Harvester & Depth Queue
 * - High-Density Data Matrix & Bulk Triage
 * - Multi-Repo Daily Intelligence Briefs
 * - 20-Runner Cloud Swarm Fleet Controller
 */

function radarApp() {
  return {
    activeTab: 'feed',
    feedView: 'cards', // 'cards' or 'compact'
    queries: [],
    stats: {},
    categories: [],
    reports: [],
    logs: [],
    loading: false,

    // Input Keywords (Left Pane in Radar Feed)
    inputKeywords: [],
    inputKeywordsTotal: 0,
    selectedRootTerm: '',
    inputSearch: '',
    inputCategory: 'all',
    inputStatus: 'all',
    inputSort: 'gaps', // 'gaps', 'name', 'depth'

    // Result Pagination & Filtering
    page: 1,
    limit: 24,
    totalItems: 0,
    totalPages: 1,
    quickFilter: 'all', // 'all', 'critical_85', 'high_65', 'breakouts', 'confirmed', 'snoozed'

    filters: {
      search: '',
      category: 'all',
      archetype: 'all',
      verdict: 'all',
      min_score: 0,
    },

    // Frontier Queue State
    frontierStats: {},
    frontierItems: [],
    frontierPage: 1,
    frontierTotalPages: 1,
    frontierSearch: '',
    frontierCategory: 'all',
    frontierStatus: 'all',
    frontierDepth: 'all',

    // Add Seed Modal & AI Preset Expander
    showAddSeedModal: false,
    newSeedTerm: '',
    newSeedCategory: 'Developer & Cloud',
    selectedPresetAngle: 'tools',
    expandedSeeds: [],
    expandingSeeds: false,

    // SERP Comparison Modal (Ahrefs-Grade SERP Similarity)
    showCompareModal: false,
    compareQ1: '',
    compareQ2: '',
    compareLoading: false,
    compareResult: null,

    // Bulk selection in Data Matrix
    selectedRows: [],

    // AI Blueprint Modal
    showBlueprintModal: false,
    activeBlueprint: {},
    copiedPrompt: false,

    // Cookie & Fleet Swarm Status
    cookieStatus: {},
    fleetData: { repositories: [], total_concurrent_runners: 20 },
    fleetDispatching: false,
    fleetSyncing: false,
    fleetMessage: '',
    dispatchBatches: 3,

    // Scan state
    scanState: {
      is_scanning: false,
      progress: 0,
      total: 0,
      message: 'Idle',
      last_run: null,
    },

    // Daily Reports
    selectedReport: '',
    selectedReportContent: '',
    reportRepoFilter: 'all',

    // Live Auditing State
    isAuditingBatch: false,

    init() {
      this.initApp();
    },

    async initApp() {
      await this.loadCategories();
      await this.loadStats();
      await this.loadInputKeywords();
      await this.loadQueries(1);
      await this.loadFrontierStats();
      await this.loadFrontier(1);
      await this.loadCookieStatus();
      await this.loadFleetStatus();
      await this.loadReports();
      await this.loadLogs();

      // Background telemetry polling every 4s
      setInterval(() => {
        this.loadStats();
        if (this.scanState.is_scanning) {
          this.loadQueries(this.page);
          this.loadInputKeywords();
          this.loadFrontierStats();
          this.loadLogs();
        }
      }, 4000);
    },

    async loadCategories() {
      try {
        const resp = await fetch('/api/categories');
        this.categories = await resp.json();
      } catch (e) {
        console.error('Failed to load categories', e);
      }
    },

    async loadStats() {
      try {
        const resp = await fetch('/api/stats');
        const data = await resp.json();
        this.stats = data;
        if (data.scan_state) {
          this.scanState = data.scan_state;
        }
      } catch (e) {
        console.error('Failed to load stats', e);
      }
    },

    // -------------------------------------------------------------
    // INPUT KEYWORDS (LEFT PANE)
    // -------------------------------------------------------------
    async loadInputKeywords() {
      try {
        const params = new URLSearchParams({
          category: this.inputCategory,
          status: this.inputStatus,
          search: this.inputSearch,
          limit: '200',
        });
        const resp = await fetch(`/api/input-keywords?${params.toString()}`);
        const data = await resp.json();
        let items = data.items || [];

        // Sorting
        if (this.inputSort === 'gaps') {
          items.sort((a, b) => (b.queries_extracted || 0) - (a.queries_extracted || 0));
        } else if (this.inputSort === 'recent') {
          items.sort((a, b) => (b.last_explored_at || '').localeCompare(a.last_explored_at || ''));
        } else if (this.inputSort === 'name') {
          items.sort((a, b) => a.niche_term.localeCompare(b.niche_term));
        } else if (this.inputSort === 'depth') {
          items.sort((a, b) => (a.depth_level || 0) - (b.depth_level || 0));
        }

        this.inputKeywords = items;
        this.inputKeywordsTotal = data.total || 0;
      } catch (e) {
        console.error('Failed to load input keywords', e);
      }
    },

    selectRootTerm(term) {
      if (this.selectedRootTerm === term) {
        this.selectedRootTerm = '';
      } else {
        this.selectedRootTerm = term;
      }
      this.page = 1;
      this.loadQueries(1);
    },

    clearRootTerm() {
      this.selectedRootTerm = '';
      this.page = 1;
      this.loadQueries(1);
    },

    // -------------------------------------------------------------
    // DISCOVERED SEARCH GAPS (RIGHT PANE / MATRIX)
    // -------------------------------------------------------------
    async loadQueries(targetPage = 1) {
      this.loading = true;
      this.page = targetPage;

      let effectiveMinScore = this.filters.min_score;
      let effectiveVerdict = this.filters.verdict;
      let effectiveTrendType = 'all';
      let effectiveUntouchedOnly = false;

      if (this.quickFilter === 'pure_gold') {
        effectiveMinScore = 80;
        effectiveUntouchedOnly = true;
      } else if (this.quickFilter === 'critical_85') {
        effectiveMinScore = 85;
      } else if (this.quickFilter === 'high_65') {
        effectiveMinScore = 65;
      } else if (this.quickFilter === 'breakouts') {
        effectiveTrendType = 'BREAKOUT';
      } else if (this.quickFilter === 'confirmed') {
        effectiveVerdict = 'confirmed_gold';
      } else if (this.quickFilter === 'snoozed') {
        effectiveVerdict = 'snoozed';
      }

      const params = new URLSearchParams({
        category: this.filters.category,
        archetype: this.filters.archetype,
        verdict: effectiveVerdict,
        min_score: effectiveMinScore,
        search: this.filters.search,
        page: this.page,
        limit: this.limit,
      });

      if (effectiveTrendType !== 'all') {
        params.append('trend_type', effectiveTrendType);
      }
      if (effectiveUntouchedOnly) {
        params.append('untouched_only', 'true');
      }

      if (this.selectedRootTerm) {
        params.append('root', this.selectedRootTerm);
      }

      try {
        const resp = await fetch(`/api/queries?${params.toString()}`);
        const data = await resp.json();
        this.queries = data.items || [];
        this.totalItems = data.total || 0;
        this.totalPages = data.total_pages || 1;
      } catch (e) {
        console.error('Failed to load queries', e);
      } finally {
        this.loading = false;
      }
    },

    setQuickFilter(qf) {
      this.quickFilter = qf;
      this.page = 1;
      this.loadQueries(1);
    },

    setCategory(cat) {
      this.filters.category = cat;
      this.inputCategory = cat;
      this.page = 1;
      this.loadQueries(1);
      this.loadInputKeywords();
    },

    async setVerdict(id, verdict) {
      try {
        const resp = await fetch('/api/verdict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, verdict }),
        });
        if (resp.ok) {
          const item = this.queries.find(q => q.id === id);
          if (item) item.human_verdict = verdict;
          await this.loadStats();
        }
      } catch (e) {
        console.error('Failed to update verdict', e);
      }
    },

    // -------------------------------------------------------------
    // LIVE SERP AUDITING & VOID VERIFICATION
    // -------------------------------------------------------------
    async auditSerpLive(item) {
      if (!item || item._auditing) return;
      item._auditing = true;
      try {
        const resp = await fetch('/api/serp/audit-live', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: item.id, keyword: item.keyword }),
        });
        const res = await resp.json();
        if (resp.ok) {
          item.exact_title_matches = res.exact_title_matches;
          item.top_competitor_title = res.top_competitor_title;
          item.top_competitor_url = res.top_competitor_url;
          item.gap_score = res.new_score;
          if (res.evidence) item.evidence = res.evidence;
          await this.loadStats();
        }
      } catch (e) {
        console.error('Failed to live-audit SERP', e);
      } finally {
        item._auditing = false;
      }
    },

    async auditBatchLive() {
      const unverified = this.queries.filter(q => q.exact_title_matches === null || q.exact_title_matches === undefined);
      if (!unverified.length) {
        alert('All visible items on this page are already verified!');
        return;
      }
      this.isAuditingBatch = true;
      try {
        for (const item of unverified.slice(0, 10)) {
          await this.auditSerpLive(item);
          await new Promise(r => setTimeout(r, 600));
        }
      } finally {
        this.isAuditingBatch = false;
      }
    },

    // -------------------------------------------------------------
    // DATA MATRIX BULK OPERATIONS
    // -------------------------------------------------------------
    toggleRowSelection(id) {
      const idx = this.selectedRows.indexOf(id);
      if (idx > -1) {
        this.selectedRows.splice(idx, 1);
      } else {
        this.selectedRows.push(id);
      }
    },

    toggleSelectAll() {
      if (this.selectedRows.length === this.queries.length) {
        this.selectedRows = [];
      } else {
        this.selectedRows = this.queries.map(q => q.id);
      }
    },

    async executeBulkVerdict(verdict) {
      if (!this.selectedRows.length) return;
      try {
        const resp = await fetch('/api/bulk-verdict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedRows, verdict }),
        });
        if (resp.ok) {
          this.queries.forEach(q => {
            if (this.selectedRows.includes(q.id)) {
              q.human_verdict = verdict;
            }
          });
          this.selectedRows = [];
          await this.loadStats();
        }
      } catch (e) {
        console.error('Bulk verdict failed', e);
      }
    },

    exportData(format = 'csv') {
      window.open(`/api/export?format=${format}`, '_blank');
    },

    // -------------------------------------------------------------
    // FRONTIER HARVESTER & QUEUE
    // -------------------------------------------------------------
    async loadFrontierStats() {
      try {
        const resp = await fetch('/api/frontier/stats');
        this.frontierStats = await resp.json();
      } catch (e) {
        console.error('Failed to load frontier stats', e);
      }
    },

    async loadFrontier(page = 1) {
      this.frontierPage = page;
      const params = new URLSearchParams({
        category: this.frontierCategory,
        status: this.frontierStatus,
        depth: this.frontierDepth,
        search: this.frontierSearch,
        page: this.frontierPage,
        limit: 30,
      });
      try {
        const resp = await fetch(`/api/frontier?${params.toString()}`);
        const data = await resp.json();
        this.frontierItems = data.items || [];
        this.frontierTotalPages = data.total_pages || 1;
      } catch (e) {
        console.error('Failed to load frontier queue', e);
      }
    },

    async triggerHarvester() {
      try {
        await fetch('/api/frontier/harvest', { method: 'POST' });
        await this.loadFrontierStats();
        await this.loadInputKeywords();
        alert('Multi-source harvester launched in background! Frontier queue expanding...');
      } catch (e) {
        console.error('Failed to trigger harvester', e);
      }
    },

    async addCustomSeed() {
      if (!this.newSeedTerm.trim()) return;
      try {
        const resp = await fetch('/api/frontier/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            term: this.newSeedTerm.trim(),
            category: this.newSeedCategory,
          }),
        });
        if (resp.ok) {
          this.newSeedTerm = '';
          this.showAddSeedModal = false;
          await this.loadFrontierStats();
          await this.loadInputKeywords();
          await this.loadFrontier(1);
        }
      } catch (e) {
        console.error('Failed to add custom seed', e);
      }
    },

    // -------------------------------------------------------------
    // 1-CLICK AI BUILDER BLUEPRINT GENERATOR
    // -------------------------------------------------------------
    openBlueprint(item) {
      const q = item.keyword;
      const arch = item.archetype || 'Micro-Tool';
      const cat = item.category || 'General';

      let stack = 'Static HTML + Alpine.js + Tailwind CSS (Cloudflare Pages / Vercel)';
      let seoTitle = `${q.charAt(0).toUpperCase() + q.slice(1)} — Free Online Tool (2025)`;
      let prompt = '';

      if (arch === 'Micro-Tool') {
        stack = 'Static Single-Page HTML/Wasm + Tailwind (Zero Backend, $0 Hosting)';
        seoTitle = `Free ${q.charAt(0).toUpperCase() + q.slice(1)} — Instant & No Signup`;
        prompt = `Act as an expert frontend engineer. Build a lightweight, responsive, single-page web utility for: "${q}".
- Target User: People searching for "${q}" needing immediate results.
- Architecture: Pure clientside JavaScript/Wasm with dark mode styling using Tailwind CSS.
- Key Features:
  1. Instant input slider/fields with zero required login.
  2. Live recalculation on change.
  3. One-click copy/export to clipboard or PDF.
  4. Structured JSON-LD FAQ Schema markup for programmatic SEO.
Make it production-ready in a single self-contained index.html file.`;
      } else if (arch === 'Workaround') {
        stack = 'Astro / Next.js Static Markdown Guide with Copy Snippets';
        seoTitle = `How to Fix ${q} — Step-by-Step Workaround (2025)`;
        prompt = `Act as a senior technical documentation engineer. Write a definitive, minimal, high-ranking troubleshooting guide for: "${q}".
- Exact Problem: Why does "${q}" happen in practice?
- Quick Fix: 30-second copy-paste solution for 80% of users.
- Deep Dive: Root cause explanation with step-by-step verified instructions.
- Edge Cases: Alternative OS/environment configurations.
Format in clean Markdown with copyable syntax-highlighted code blocks.`;
      } else if (arch === 'Template') {
        stack = 'Downloadable Template (Google Sheets / Notion / GitHub Scaffold)';
        seoTitle = `${q.charAt(0).toUpperCase() + q.slice(1)} — Free Download & Template`;
        prompt = `Design a comprehensive, professional template and boilerplate for: "${q}".
- Target Persona: Teams and indie makers looking for "${q}".
- Core Structure: Clean layout, pre-filled formulas/configs, and instructions.
- Provide both a copyable raw config/scaffold and a printable checklist.`;
      } else {
        stack = 'Production-Ready Boilerplate & Canonical Recipe';
        seoTitle = `${q} — Canonical Recipe & Production Boilerplate`;
        prompt = `Build a high-quality developer boilerplate repository for: "${q}".
- Include full docker-compose / setup commands, clean modular structure, zero deprecated packages.
- Add comprehensive README with 1-click deploy to Vercel/Render.`;
      }

      this.activeBlueprint = {
        keyword: q,
        archetype: arch,
        category: cat,
        stack,
        seo_title: seoTitle,
        prompt,
      };
      this.copiedPrompt = false;
      this.showBlueprintModal = true;
    },

    copyBlueprintPrompt() {
      if (this.activeBlueprint && this.activeBlueprint.prompt) {
        navigator.clipboard.writeText(this.activeBlueprint.prompt);
        this.copiedPrompt = true;
        setTimeout(() => {
          this.copiedPrompt = false;
        }, 2500);
      }
    },

    // -------------------------------------------------------------
    // DAILY BRIEFS (REPORTS)
    // -------------------------------------------------------------
    async loadReports() {
      try {
        const resp = await fetch('/api/reports');
        this.reports = await resp.json();
        if (this.reports.length && !this.selectedReport) {
          this.viewReport(this.reports[0].filename);
        }
      } catch (e) {
        console.error('Failed to load reports', e);
      }
    },

    async viewReport(filename) {
      this.selectedReport = filename;
      try {
        const resp = await fetch(`/api/reports/${encodeURIComponent(filename)}`);
        const mdText = await resp.text();
        this.selectedReportContent = marked.parse(mdText);
      } catch (e) {
        this.selectedReportContent = '<p class="text-red-400">Error loading report.</p>';
      }
    },

    // -------------------------------------------------------------
    // CLOUD SWARM FLEET (20 RUNNERS)
    // -------------------------------------------------------------
    async loadFleetStatus() {
      try {
        const resp = await fetch('/api/fleet/status');
        this.fleetData = await resp.json();
      } catch (e) {
        console.error('Failed to load fleet status', e);
      }
    },

    async dispatchFleet(batches = 3) {
      this.fleetDispatching = true;
      this.fleetMessage = 'Triggering 20 cloud runners across 5 repositories...';
      try {
        const resp = await fetch(`/api/fleet/dispatch?batches=${batches}`, { method: 'POST' });
        const res = await resp.json();
        this.fleetMessage = res.message || 'Swarm successfully dispatched!';
        setTimeout(() => { this.fleetMessage = ''; }, 6000);
      } catch (e) {
        this.fleetMessage = 'Error dispatching swarm.';
      } finally {
        this.fleetDispatching = false;
      }
    },

    async syncFleet() {
      this.fleetSyncing = true;
      this.fleetMessage = 'Pulling reports from all 5 repositories...';
      try {
        const resp = await fetch('/api/fleet/sync', { method: 'POST' });
        const res = await resp.json();
        this.fleetMessage = 'Sync initiated. Refreshing reports in 3s...';
        setTimeout(async () => {
          await this.loadReports();
          this.fleetMessage = 'Fleet reports refreshed!';
          setTimeout(() => { this.fleetMessage = ''; }, 4000);
        }, 3000);
      } catch (e) {
        this.fleetMessage = 'Error syncing fleet.';
      } finally {
        this.fleetSyncing = false;
      }
    },

    async loadCookieStatus() {
      try {
        const resp = await fetch('/api/cookies/status');
        this.cookieStatus = await resp.json();
      } catch (e) {
        console.error('Failed to load cookie status', e);
      }
    },

    async loadLogs() {
      try {
        const resp = await fetch('/api/logs');
        this.logs = await resp.json();
      } catch (e) {
        console.error('Failed to load logs', e);
      }
    },

    async triggerScan() {
      try {
        const resp = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: this.filters.category, limit_batches: 2 }),
        });
        await this.loadStats();
      } catch (e) {
        console.error('Failed to trigger scan', e);
      }
    },

    // -------------------------------------------------------------
    // AHREFS-GRADE SERP COMPARISON (SERP SIMILARITY & OVERLAP)
    // -------------------------------------------------------------
    openCompare(q1, q2 = '') {
      this.compareQ1 = q1;
      const other = this.queries.find(q => q.keyword !== q1);
      this.compareQ2 = q2 || (other ? other.keyword : q1 + ' alternative');
      this.showCompareModal = true;
      this.runCompare();
    },

    async runCompare() {
      if (!this.compareQ1.trim() || !this.compareQ2.trim()) return;
      this.compareLoading = true;
      try {
        const params = new URLSearchParams({
          q1: this.compareQ1.trim(),
          q2: this.compareQ2.trim(),
        });
        const resp = await fetch(`/api/serp/compare?${params.toString()}`);
        this.compareResult = await resp.json();
      } catch (e) {
        console.error('Failed to run comparison', e);
      } finally {
        this.compareLoading = false;
      }
    },

    // -------------------------------------------------------------
    // AHREFS-GRADE AI PRESET ANGLE SEED EXPANDER
    // -------------------------------------------------------------
    async expandPresetSeeds() {
      if (!this.newSeedTerm.trim()) return;
      this.expandingSeeds = true;
      try {
        const resp = await fetch('/api/seeds/expand', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: this.newSeedTerm.trim(),
            preset: this.selectedPresetAngle,
          }),
        });
        const data = await resp.json();
        this.expandedSeeds = data.seeds || [];
      } catch (e) {
        console.error('Failed to expand seeds', e);
      } finally {
        this.expandingSeeds = false;
      }
    },

    async queueExpandedSeeds() {
      if (!this.expandedSeeds.length) return;
      try {
        const resp = await fetch('/api/frontier/add-batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            terms: this.expandedSeeds,
            category: this.newSeedCategory,
          }),
        });
        const res = await resp.json();
        alert(`Successfully queued ${res.added_count} targeted seeds into the Frontier!`);
        this.expandedSeeds = [];
        this.newSeedTerm = '';
        this.showAddSeedModal = false;
        await this.loadFrontierStats();
        await this.loadInputKeywords();
        await this.loadFrontier(1);
      } catch (e) {
        console.error('Failed to queue expanded seeds', e);
      }
    },
  };
}

// Make globally available & register with Alpine
window.radarApp = radarApp;
document.addEventListener('alpine:init', () => {
  if (window.Alpine) {
    window.Alpine.data('radarApp', radarApp);
  }
});
