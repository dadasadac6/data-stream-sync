/**
 * Gold Miner Radar UI Application (Alpine.js State Manager)
 */

function radarApp() {
  return {
    activeTab: 'feed',
    queries: [],
    stats: {},
    categories: [],
    reports: [],
    logs: [],
    loading: false,
    selectedReport: '',
    selectedReportContent: '',
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
      min_score: 0
    },

    // Admin & Scan controls
    adminScanCategory: 'All',
    adminBatchDepth: 1,
    scanState: {
      is_scanning: false,
      progress: 0,
      total: 0,
      message: 'Idle',
      last_run: null
    },
    pollInterval: null,

    async initApp() {
      await this.loadCategories();
      await this.loadStats();
      await this.loadQueries();
      await this.loadReports();
      await this.loadLogs();

      // Poll stats every 4 seconds
      setInterval(() => {
        this.loadStats();
        if (this.scanState.is_scanning) {
          this.loadQueries();
          this.loadLogs();
        }
      }, 4000);
    },

    async loadCategories() {
      try {
        const res = await fetch('/api/categories');
        if (res.ok) {
          this.categories = await res.json();
        }
      } catch (err) {
        console.error("Failed to load categories:", err);
      }
    },

    async loadStats() {
      try {
        const res = await fetch('/api/stats');
        if (res.ok) {
          const data = await res.json();
          this.stats = data;
          if (data.scan_state) {
            this.scanState = data.scan_state;
          }
        }
      } catch (err) {
        console.error("Failed to load stats:", err);
      }
    },

    async loadQueries() {
      this.loading = true;
      try {
        const params = new URLSearchParams({
          category: this.filters.category,
          archetype: this.filters.archetype,
          verdict: this.filters.verdict,
          min_score: this.filters.min_score,
          search: this.filters.search,
          page: this.page,
          limit: this.limit
        });

        const res = await fetch(`/api/queries?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          this.queries = data.items || [];
          this.totalItems = data.total || 0;
          this.totalPages = data.total_pages || 1;
        }
      } catch (err) {
        console.error("Failed to load queries:", err);
      } finally {
        this.loading = false;
      }
    },

    changePage(newPage) {
      if (newPage >= 1 && newPage <= this.totalPages) {
        this.page = newPage;
        this.loadQueries();
      }
    },

    async setVerdict(queryId, verdict) {
      try {
        const res = await fetch('/api/verdict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: queryId, verdict })
        });
        if (res.ok) {
          // Update item in local list instantly
          const item = this.queries.find(q => q.id === queryId);
          if (item) {
            item.human_verdict = verdict;
          }
          this.loadStats();
        }
      } catch (err) {
        console.error("Failed to update verdict:", err);
      }
    },

    async triggerScan() {
      try {
        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: 'All', limit_batches: 1 })
        });
        if (res.ok) {
          const data = await res.json();
          this.scanState.is_scanning = true;
          this.scanState.message = 'Scan initialized...';
        }
      } catch (err) {
        console.error("Scan trigger error:", err);
      }
    },

    async triggerCustomScan() {
      try {
        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            category: this.adminScanCategory,
            limit_batches: parseInt(this.adminBatchDepth, 10)
          })
        });
        if (res.ok) {
          this.scanState.is_scanning = true;
          this.scanState.message = `Scan started for ${this.adminScanCategory}...`;
          this.activeTab = 'feed';
        }
      } catch (err) {
        console.error("Custom scan trigger error:", err);
      }
    },

    async loadReports() {
      try {
        const res = await fetch('/api/reports');
        if (res.ok) {
          this.reports = await res.json();
          if (this.reports.length > 0 && !this.selectedReport) {
            this.loadReportContent(this.reports[0].filename);
          }
        }
      } catch (err) {
        console.error("Failed to load reports list:", err);
      }
    },

    async loadReportContent(filename) {
      this.selectedReport = filename;
      try {
        const res = await fetch(`/api/reports/${encodeURIComponent(filename)}`);
        if (res.ok) {
          const mdText = await res.text();
          this.selectedReportContent = mdText;
          const container = document.getElementById('report-view');
          if (container && window.marked) {
            container.innerHTML = window.marked.parse(mdText);
          }
        }
      } catch (err) {
        console.error("Failed to read report:", err);
      }
    },

    async loadLogs() {
      try {
        const res = await fetch('/api/logs?limit=40');
        if (res.ok) {
          this.logs = await res.json();
        }
      } catch (err) {
        console.error("Failed to load logs:", err);
      }
    },

    exportData(format) {
      const url = `/api/export?format=${format}&category=${encodeURIComponent(this.filters.category)}&min_score=${this.filters.min_score}`;
      window.open(url, '_blank');
    },

    getArchetypeIcon(archetype) {
      switch (archetype) {
        case 'Micro-Tool': return '🛠️';
        case 'Workaround': return '🐛';
        case 'Recipe': return '📋';
        case 'Breaking News': return '⚡';
        default: return '💡';
      }
    },

    formatBytes(bytes) {
      if (!bytes) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
  };
}
