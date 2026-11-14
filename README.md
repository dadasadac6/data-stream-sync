# Data Stream Sync

A modular data synchronization and local analytics state engine.

## Overview

Data Stream Sync provides structured event logging, local relational persistence, and telemetry status monitoring.

- **Structured Ingestion:** Validates and processes incoming record streams.
- **Local Persistence:** SQLite-backed transaction store with WAL mode for local caching and querying.
- **Diagnostic Metrics:** Lightweight monitoring endpoints for service health and record counters.

## Architecture

```
├── config/                   # Configuration schemas and category seeds
├── engines/                  # Ingestion, validation, and scoring engines
├── storage/                  # SQLite persistence and query layer
├── reports/                  # Formatted summary reports
└── dashboard.py              # Diagnostic monitoring service
```

## Quick Start

### 1. Launch Diagnostic Monitor
```bash
python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8080
```
Visit `http://localhost:8080` to view the service health and metrics dashboard.
