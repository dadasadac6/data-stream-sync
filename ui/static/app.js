/**
 * Gold Miner Radar UI Application (Alpine.js State Manager v6.0)
 * Manages Live Feed (Cards & Compact), Frontier Queue, Bulk Actions, 
 * AI Builder Blueprint Generator, and Swarm Telemetry.
 */

function radarApp() {
  return {
    activeTab: 'feed',
    feedView: 'cards',
    queries: [],
    stats: {},
    categories: [],
    reports: [],
    logs: [],
    loading: false,

    // Pagination
    page: 1,
    limit: 20,
    totalItems: 0,
    totalPages: 1,

    // Filters
    filters: {
      search: '',
      category: 'all',
      archetype: 'all',
      verdict: 'all',
      min_score: 0,
    },

    // Frontier Queue state
    frontierStats: {},
    frontierItems: [],
    frontierPage: 1,
    frontierTotalPages: 1,
    newSeedTerm: '',
    newSeedCategory: 'Developer & Cloud',

    // Bulk selection
    selectedRows: [],

    // AI Blueprint Modal
    showBlueprintModal: false,
    activeBlueprint: {},
    copiedPrompt: false,

    // Cookie & Swarm Status
    cookieStatus: {},
    fleetData: { repositories: [], total_concurrent_runners: 20 },
    fleetDispatching: false,
    fleetSyncing: false,
    fleetMessage: '',
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

    async initApp() {
      await this.loadCategories();
      await this.loadStats();
      await this.loadQueries(1);
      await this.loadFrontierStats();
      await this.loadFrontier(1);
      await this.loadCookieStatus();
      await this.loadFleetStatus();
      await this.loadReports();
      await this.loadLogs();

      // Poll stats every 4 seconds
      setInterval(() => {
        this.loadStats();
        if (this.scanState.is_scanning) {
          this.loadQueries(this.page);
          this.loadFrontierStats();
          this.loadLogs();
        }
      }, 4000);
    },

    async loadCategories() {
      try {
        const resp = await fetch('/api/categories');
        this.categories = await resp.json();
        if (this.categories.length) {
          this.newSeedCategory = this.categories[0];
        }
      } catch (e) {
        console.error('Failed to load categories', e);
      }
    },

    async setCategory(cat) {
      this.filters.category = cat;
      await this.loadQueries(1);
      if (this.activeTab === 'frontier') {
        await this.loadFrontier(1);
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

    async loadQueries(targetPage = 1) {
      this.loading = true;
      this.page = targetPage;
      const params = new URLSearchParams({
        category: this.filters.category,
        archetype: this.filters.archetype,
        verdict: this.filters.verdict,
        min_score: this.filters.min_score,
        search: this.filters.search,
        page: this.page,
        limit: this.limit,
      });

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

    async setVerdict(id, verdict) {
      try {
        const resp = await fetch('/api/verdict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, verdict }),
        });
        if (resp.ok) {
          // Update in-memory
          const item = this.queries.find((q) => q.id === id);
          if (item) item.human_verdict = verdict;
          await this.loadStats();
        }
      } catch (e) {
        console.error('Failed to set verdict', e);
      }
    },

    // Bulk Actions
    toggleSelectAll(e) {
      if (e.target.checked) {
        this.selectedRows = this.queries.map((q) => q.id);
      } else {
        this.selectedRows = [];
      }
    },

    async bulkSetVerdict(verdict) {
      if (!this.selectedRows.length) return;
      try {
        const resp = await fetch('/api/bulk-verdict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedRows, verdict }),
        });
        if (resp.ok) {
          await this.loadQueries(this.page);
          await this.loadStats();
          this.selectedRows = [];
        }
      } catch (e) {
        console.error('Failed to bulk set verdict', e);
      }
    },

    // Frontier Queue
    async loadFrontierStats() {
      try {
        const resp = await fetch('/api/frontier/stats');
        this.frontierStats = await resp.json();
      } catch (e) {
        console.error('Failed to load frontier stats', e);
      }
    },

    async loadFrontier(targetPage = 1) {
      this.frontierPage = targetPage;
      const params = new URLSearchParams({
        category: this.filters.category,
        page: this.frontierPage,
        limit: 30,
      });

      try {
        const resp = await fetch(`/api/frontier?${params.toString()}`);
        const data = await resp.json();
        this.frontierItems = data.items || [];
        this.frontierTotalPages = data.total_pages || 1;
      } catch (e) {
        console.error('Failed to load frontier page', e);
      }
    },

    async addSeed() {
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
        const res = await resp.json();
        this.newSeedTerm = '';
        await this.loadFrontierStats();
        await this.loadFrontier(1);
      } catch (e) {
        console.error('Failed to add seed', e);
      }
    },

    // Cookie Status
    async loadCookieStatus() {
      try {
        const resp = await fetch('/api/cookies/status');
        this.cookieStatus = await resp.json();
      } catch (e) {
        console.error('Failed to load cookie status', e);
      }
    },

    // 1-Click AI Builder Blueprint Generator
    openBlueprint(item) {
      const q = item.keyword;
      const arch = item.archetype || 'Micro-Tool';
      const cat = item.category || 'General';

      let stack = 'Static HTML + Alpine.js + Tailwind CSS (Cloudflare Pages)';
      let seoTitle = `${q.charAt(0).toUpperCase() + q.slice(1)} — Free Online Tool (2025)`;
      let prompt = '';

      if (arch === 'Micro-Tool') {
        stack = 'Static Single-Page HTML/Wasm + Tailwind (Zero Backend)';
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
        stack = 'Programmatic Comparison Table (Next.js / Astro)';
        seoTitle = `${q} — In-Depth Feature & Pricing Comparison`;
        prompt = `Build a high-converting, objective comparison matrix for: "${q}".
- Compare core features, pricing, open source vs hosted tradeoffs, and real-world benchmarks.
- Provide a summary verdict recommendation matrix.`;
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
        }, 3000);
      }
    },

    // Daily Reports
    async loadReports() {
      try {
        const resp = await fetch('/api/reports');
        this.reports = await resp.json();
        if (this.reports.length && !this.selectedReport) {
          await this.loadReport(this.reports[0].filename);
        }
      } catch (e) {
        console.error('Failed to load reports', e);
      }
    },

    async loadReport(filename) {
      this.selectedReport = filename;
      try {
        const resp = await fetch(`/api/reports/${encodeURIComponent(filename)}`);
        const mdText = await resp.text();
        this.selectedReportContent = marked.parse(mdText);
      } catch (e) {
        this.selectedReportContent = '<p class="text-red-400">Error loading report.</p>';
      }
    },

    // Live Logs
    async loadLogs() {
      try {
        const resp = await fetch('/api/logs');
        this.logs = await resp.json();
      } catch (e) {
        console.error('Failed to load logs', e);
      }
    },

    // Manual Scan Trigger
    async triggerScan() {
      try {
        const resp = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: this.filters.category, limit_batches: 2 }),
        });
        const data = await resp.json();
        await this.loadStats();
      } catch (e) {
        console.error('Failed to trigger scan', e);
      }
    },

    // Fleet Swarm Controls
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
  };
}
