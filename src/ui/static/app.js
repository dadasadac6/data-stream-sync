/**
 * Data Stream Sync UI Application (Alpine.js State Manager v7.0)
 * Modern Zero-Scroll Workspace:
 * - Two-Pane Niche Radar (Input Keywords Explorer + Discovered Results)
 * - Frontier Harvester & Depth Queue
 * - High-Density Data Matrix & Bulk Triage
 * - Multi-Repo Daily Intelligence Briefs
 * - Cloud Stream Controller
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
    inputSort: 'best_clusters', // 'best_clusters', 'gaps', 'recent', 'name', 'depth'

    // Result Pagination & Filtering
    page: 1,
    limit: 24,
    totalItems: 0,
    totalPages: 1,
    quickFilter: 'all', // 'all', 'best_picks', 'voids', 'competed', 'pending', 'pure_gold', 'critical_85', 'high_65', 'breakouts', 'confirmed'
    sortBy: 'best_to_build',
    sortOrder: 'DESC',

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
    downloadedBlueprint: false,

    // Global Toast Notification
    toast: {
      show: false,
      message: '',
      type: 'info',
      timeout: null
    },

    showToast(message, type = 'info', duration = 3200) {
      if (this.toast.timeout) clearTimeout(this.toast.timeout);
      this.toast.message = message;
      this.toast.type = type;
      this.toast.show = true;
      this.toast.timeout = setTimeout(() => {
        this.toast.show = false;
      }, duration);
    },

    // Live Google Trends Feed
    liveTrends: [],
    selectedTrendGeo: 'US',
    trendsSearch: '',
    isTrendsLoading: false,
    trendIngestStatus: {},

    // Autonomous Auto-Pilot
    autopilot: {
      is_active: false,
      last_run: null,
      cycles_completed: 0,
      current_status: 'Idle'
    },

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
    recheckingTerm: '',

    get selectedRootItem() {
      if (!this.selectedRootTerm) return null;
      return this.inputKeywords.find(k => k.niche_term === this.selectedRootTerm) || null;
    },

    get isSelectedRootPending() {
      const item = this.selectedRootItem;
      return item ? (item.status === 'pending' && !item.queries_extracted) : false;
    },

    get filteredLiveTrends() {
      if (!this.trendsSearch || !this.trendsSearch.trim()) return this.liveTrends;
      const q = this.trendsSearch.trim().toLowerCase();
      return (this.liveTrends || []).filter(t => 
        (t.title && t.title.toLowerCase().includes(q)) || 
        (t.category && t.category.toLowerCase().includes(q)) ||
        (t.snippet && t.snippet.toLowerCase().includes(q))
      );
    },

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
      await this.fetchAutopilotStatus();

      // Background telemetry polling every 4s
      setInterval(() => {
        this.loadStats();
        this.fetchAutopilotStatus();
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
          sort_by: this.inputSort,
          limit: '200',
        });
        const resp = await fetch(`/api/input-keywords?${params.toString()}`);
        const data = await resp.json();
        let items = data.items || [];

        // Sorting
        if (this.inputSort === 'best_clusters') {
          items.sort((a, b) => (b.cluster_doability_rank || 0) - (a.cluster_doability_rank || 0));
        } else if (this.inputSort === 'gaps') {
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
        // Reset quickFilter to 'all' so all opportunities for this specific root are immediately visible
        this.quickFilter = 'all';
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
      let effectiveCompetition = 'all';

      if (this.quickFilter === 'best_picks') {
        effectiveCompetition = 'best_picks';
      } else if (this.quickFilter === 'voids') {
        effectiveCompetition = 'void';
      } else if (this.quickFilter === 'competed') {
        effectiveCompetition = 'competed';
      } else if (this.quickFilter === 'pending') {
        effectiveCompetition = 'pending';
      } else if (this.quickFilter === 'pure_gold') {
        effectiveMinScore = 80;
        effectiveCompetition = 'void';
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
        sort_by: this.sortBy || 'gap_score',
        sort_order: this.sortOrder || 'DESC',
        page: this.page,
        limit: this.limit,
      });

      if (effectiveTrendType !== 'all') {
        params.append('trend_type', effectiveTrendType);
      }
      if (effectiveCompetition !== 'all') {
        params.append('competition_status', effectiveCompetition);
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

    handleSortChange(val) {
      if (val === 'best_to_build') {
        this.sortBy = 'best_to_build';
        this.sortOrder = 'DESC';
      } else if (val === 'competed_first') {
        this.sortBy = 'exact_title_matches';
        this.sortOrder = 'DESC';
      } else if (val === 'exact_title_matches') {
        this.sortBy = 'exact_title_matches';
        this.sortOrder = 'ASC';
      } else if (val === 'pending_first') {
        this.sortBy = 'pending_first';
        this.sortOrder = 'DESC';
      } else if (val === 'keyword') {
        this.sortBy = 'keyword';
        this.sortOrder = 'ASC';
      } else {
        this.sortBy = val;
        this.sortOrder = 'DESC';
      }
      this.page = 1;
      this.loadQueries(1);
    },

    setCategory(cat) {
      this.filters.category = cat;
      this.inputCategory = cat;
      this.selectedRootTerm = '';
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
        this.showToast('All visible items on this page are already verified!', 'info');
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

    async recheckNiche(term, category) {
      if (!term || this.recheckingTerm === term) return;
      this.recheckingTerm = term;
      try {
        const resp = await fetch('/api/probe/instant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ term, category: category || 'Developer & Cloud' }),
        });
        if (resp.ok) {
          this.showToast(`⚡ Instant live probe launched for "${term}"! Evaluating Google Trends & SERP voids in background...`, 'success');
          setTimeout(() => { this.loadQueries(1); this.loadInputKeywords(); this.loadStats(); }, 5000);
          setTimeout(() => { this.loadQueries(1); this.loadInputKeywords(); this.loadStats(); }, 15000);
        }
      } catch (e) {
        console.error('Failed to trigger recheck', e);
      } finally {
        this.recheckingTerm = '';
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
        this.showToast('Multi-source harvester launched in background! Frontier queue expanding...', 'info');
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
          this.showToast('New topic successfully added to Frontier scan queue!', 'success');
        }
      } catch (e) {
        console.error('Failed to add custom seed', e);
      }
    },

    // -------------------------------------------------------------
    // EXPORT OPPORTUNITIES (CSV / JSON)
    // -------------------------------------------------------------
    exportData(format = 'csv') {
      if (!this.queries || !this.queries.length) {
        this.showToast('No search gap opportunities available to export.', 'warning');
        return;
      }
      const timestamp = new Date().toISOString().slice(0, 10);
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(this.queries, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `telemetry_opportunities_${timestamp}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const headers = ['Search Keyword', 'Opportunity Score', 'Tool Format', 'Category', 'Trend Velocity', 'Google Top 10 Matches', 'Top Competitor Title', 'Top Competitor URL', 'Status'];
        const rows = this.queries.map(q => [
          `"${(q.keyword || '').replace(/"/g, '""')}"`,
          q.gap_score || 0,
          `"${(q.archetype || '').replace(/"/g, '""')}"`,
          `"${(q.category || '').replace(/"/g, '""')}"`,
          `"${(q.trend_velocity || '').replace(/"/g, '""')}"`,
          q.exact_title_matches !== null ? `${q.exact_title_matches}/10` : 'Not Checked',
          `"${(q.top_competitor_title || '').replace(/"/g, '""')}"`,
          `"${(q.top_competitor_url || '').replace(/"/g, '""')}"`,
          `"${(q.human_verdict || 'pending')}"`
        ]);
        const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `telemetry_opportunities_${timestamp}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    },

    // -------------------------------------------------------------
    // 1-CLICK WEBSITE SILO BLUEPRINT GENERATOR (Discovery Engine v3.0)
    // -------------------------------------------------------------
    async openBlueprint(item) {
      const q = item.keyword;
      const cat = item.category || 'General';
      const clusterKws = item.cluster_kws || 1;
      const isVoid = item.exact_title_matches === 0;

      // Clean domain slugs
      const words = q.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(w => !['a','the','in','for','to','of','with','and','or','how'].includes(w)).slice(0, 3);
      const capSlug = words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('');
      const domains = [
        `${capSlug}HQ.com`,
        `${capSlug}Guide.com`,
        `The${capSlug}Hub.com`
      ];

      // Monetization tier
      const rpmTiers = {
        'Finance & Wealth': { rpm: 'High ($55 - $125 RPM)', bounty: '$75 - $150 / lead', model: 'High-Ticket Financial Lead Gen & Affiliate' },
        'Legal & Compliance': { rpm: 'High ($65 - $150 RPM)', bounty: '$60 - $120 / sale', model: 'Legal Template Downloads & Attorney Referrals' },
        'Small Business & B2B': { rpm: 'High ($50 - $110 RPM)', bounty: '$50 - $100 / lead', model: 'B2B Software Trials & Commercial Templates' },
        'Clean Energy & Home': { rpm: 'High ($40 - $95 RPM)', bounty: '$40 - $85 / quote', model: 'Contractor Quote Leads & Equipment Affiliates' },
        'Real Estate & Living': { rpm: 'Medium-High ($35 - $80 RPM)', bounty: '$30 - $70 / lead', model: 'Property Management & Inspection Leads' },
        'Health & Fitness': { rpm: 'Medium ($25 - $60 RPM)', bounty: '$20 - $50 / order', model: 'Direct Affiliates & Mediavine Display Ads' },
        'Travel & Visas': { rpm: 'Medium ($25 - $55 RPM)', bounty: '$15 - $45 / booking', model: 'Travel Insurance & Flight Search Affiliates' },
        'Productivity & Work': { rpm: 'Medium ($20 - $45 RPM)', bounty: '$10 - $35 / sale', model: 'Notion/SaaS Templates & Display Ads' },
      };
      const rpmData = rpmTiers[cat] || { rpm: 'Standard ($20 - $45 RPM)', bounty: '$15 - $35 / lead', model: 'Display Ads & Micro-SaaS Upgrades' };

      // Interactive lead asset
      let leadAsset = `1-Page Interactive ${q.toUpperCase()} Decision Calculator`;
      if (/template|agreement|contract|form|affidavit/.test(q)) {
        leadAsset = `Downloadable ${q.toUpperCase()} Template (Word & PDF) + Custom Clause Checklist`;
      } else if (/checklist|requirements|rules|steps/.test(q)) {
        leadAsset = `Printable ${q.toUpperCase()} Step-by-Step Compliance Checklist & Timeline`;
      } else if (/cost|price|calculator|rate/.test(q)) {
        leadAsset = `Real-Time Interactive ${q.toUpperCase()} Formula Calculator (Zero-Signup)`;
      }

      // Pillar sections
      const pillarSections = [
        `1. Comprehensive Overview: Scope, Rules & Who Needs ${q.toUpperCase()}`,
        `2. Total Costs, Price Ranges & Hidden Fees in 2026`,
        `3. Step-by-Step Execution Process & Legal Timelines`,
        `4. Common Traps, Costly Mistakes & Dispute Resolution`,
        `5. Frequently Asked Questions & Expert Recommendations`
      ];

      // Cluster sub-articles
      const clusterArticles = [
        `Is ${q.toUpperCase()} Legally Binding? (Key Clauses & Exceptions)`,
        `Step-by-Step Checklist for ${q.toUpperCase()} Before You Sign`,
        `Free ${q.toUpperCase()} Template & Sample Breakdown (2026)`,
        `${q.toUpperCase()} Cost Breakdown vs Standard Alternatives`
      ];

      // Master AI Generation Prompt
      const fullPrompt = `Act as an expert digital publisher, niche website architect, and senior SEO copywriter.
I am building a high-authority, high-converting niche website for the uncontested search topic: "${q}".

[NICHE SPECIFICATION]
- Primary Keyword: "${q}"
- Vertical: ${cat}
- Google SERP Competition: ${isVoid ? '0/10 Title Matches (Untouched Void)' : 'Weak / Forum Dominated'}
- Target Audience: Decision makers seeking definitive answers, costs, rules, and actionable templates.
- Brand Concept: ${domains[0]}

[REQUIRED WEBSITE ARCHITECTURE]
1. Cornerstone Pillar Article (2,500 words):
   - Title: "The Complete Guide to ${q.toUpperCase()} (2026 Edition)"
   - Outline:
${pillarSections.map(s => '     * ' + s).join('\n')}
   - Information Gain Differentiator: Include a structured comparison table, statutory timeline checklist, and concrete dollar figures.

2. Supporting Topical Cluster Articles (1,200 words each):
${clusterArticles.map((a, i) => `   - Article ${i+1}: "${a}"`).join('\n')}

3. Lead Magnet / Interactive Web Asset:
   - Asset: "${leadAsset}"
   - Format: Single-page responsive HTML/Tailwind tool with zero required login.

4. Programmatic SEO & Monetization:
   - Primary Model: ${rpmData.model} (${rpmData.bounty})
   - Display Ad RPM: ${rpmData.rpm}

Generate the complete, production-ready Pillar Page markdown content with FAQ schema and clear CTAs linking to the lead magnet.`;

      this.activeBlueprint = {
        keyword: q,
        category: cat,
        cluster_kws: clusterKws,
        domains: domains,
        lead_asset: leadAsset,
        rpm: rpmData.rpm,
        bounty: rpmData.bounty,
        model: rpmData.model,
        pillar_title: `The Master Guide to ${q.toUpperCase()} [2026 Edition]`,
        pillar_sections: pillarSections,
        cluster_articles: clusterArticles,
        prompt: fullPrompt,
        copiedPrompt: false
      };

      this.showBlueprintModal = true;
    },

    copyBlueprintPrompt() {
      if (this.activeBlueprint && this.activeBlueprint.prompt) {
        navigator.clipboard.writeText(this.activeBlueprint.prompt);
        this.copiedPrompt = true;
        this.showToast('📋 AI Blueprint Prompt copied to clipboard!', 'success');
        setTimeout(() => {
          this.copiedPrompt = false;
        }, 2500);
      }
    },

    downloadBlueprintPackage(topic) {
      const q = topic || (this.activeBlueprint ? this.activeBlueprint.keyword : '');
      if (!q) return;
      this.downloadedBlueprint = true;
      window.location.href = `/api/blueprint/export?topic=${encodeURIComponent(q)}`;
      this.showToast(`📥 AI Production Package downloaded for "${q}"!`, 'success');
      setTimeout(() => {
        this.downloadedBlueprint = false;
      }, 3000);
    },

    // -------------------------------------------------------------
    // LIVE GOOGLE TRENDS RSS STREAM
    // -------------------------------------------------------------
    async fetchLiveTrends(geo = 'US') {
      this.selectedTrendGeo = geo;
      this.isTrendsLoading = true;
      try {
        const res = await fetch(`/api/trends/live?geo=${geo}`);
        const data = await res.json();
        this.liveTrends = data.items || [];
      } catch (err) {
        console.error('Failed to fetch live trends:', err);
      } finally {
        this.isTrendsLoading = false;
      }
    },

    async ingestTrend(trend) {
      if (!trend || !trend.title) return;
      const key = trend.title;
      this.trendIngestStatus[key] = 'ingesting';
      this.showToast(`🚀 Ingesting & expanding breakout trend: "${trend.title}"...`, 'info');
      try {
        const res = await fetch('/api/trends/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: trend.title,
            category: trend.category || 'General',
            geo: this.selectedTrendGeo
          })
        });
        const data = await res.json();
        this.trendIngestStatus[key] = 'success';
        this.showToast(`✅ Topic "${trend.title}" ingested & clustered into Radar!`, 'success');
        await this.loadStats();
        await this.loadInputKeywords();
        setTimeout(() => {
          this.activeTab = 'feed';
          this.loadQueries(1);
        }, 1200);
      } catch (err) {
        console.error('Trend ingest error:', err);
        this.trendIngestStatus[key] = 'error';
        this.showToast(`Failed to ingest trend: ${err.message}`, 'error');
      }
    },

    // -------------------------------------------------------------
    // AUTOPILOT
    // -------------------------------------------------------------
    async fetchAutopilotStatus() {
      try {
        const res = await fetch('/api/autopilot/status');
        this.autopilot = await res.json();
      } catch (err) {
        console.error('Failed to fetch autopilot status:', err);
      }
    },

    async toggleAutopilot() {
      const nextState = !this.autopilot.is_active;
      try {
        const res = await fetch('/api/autopilot/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: nextState })
        });
        const data = await res.json();
        if (data.state) {
          this.autopilot = data.state;
        } else {
          await this.fetchAutopilotStatus();
        }
        if (this.autopilot.is_active) {
          this.showToast('🤖 Auto-Pilot turned ON: 30-min discovery cycles active', 'success');
        } else {
          this.showToast('⏸️ Auto-Pilot paused', 'info');
        }
      } catch (err) {
        console.error('Failed to toggle autopilot:', err);
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
        this.showToast(`Successfully queued ${res.added_count} targeted seeds into the Frontier!`, 'success');
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
