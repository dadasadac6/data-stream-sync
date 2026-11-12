# Ecosystem Telemetry Probe

[![Ecosystem Telemetry & Matrix Dependency Audit](https://github.com/beachjampore-lab/ecosystem-telemetry-probe/actions/workflows/telemetry.yml/badge.svg)](https://github.com/beachjampore-lab/ecosystem-telemetry-probe/actions/workflows/telemetry.yml)

Distributed runtime health probe and dependency matrix verification framework.

## Overview

The Ecosystem Telemetry Probe provides automated, zero-overhead background audits across matrix dependencies and ecosystem runtime health signals.

- **Distributed Partition Sharding:** Modular worker partitions (`shard_id % total_shards`) for high-throughput distributed execution.
- **Pure HTTP Matrix Probes:** Lightweight signal streams with randomized jitter and header rotation.
- **Persistent State Cache:** Local WAL-enabled SQLite matrix store for historical signal deduplication and cooldown enforcement.

## Architecture

```
├── config/
│   └── matrix_taxonomy.json      # Matrix category taxonomies & partition seeds
├── engines/
│   ├── evaluator.py              # Composite scoring & metric classification
│   ├── filter_pipeline.py        # Entropy sanitization & noise reduction
│   ├── index_auditor.py          # Primary index auditing & reference checks
│   ├── probe_worker.py           # Shard partition worker runner
│   ├── signal_tracer.py          # Trace auditing & secondary signal collector
│   ├── stream_sampler.py         # Batch stream extractor & jitter control
│   └── taxonomy_loader.py        # Recursive frontier queue loader
├── storage/
│   ├── db.py                     # WAL-mode state database manager
│   └── telemetry_matrix.db       # Persistent SQLite metric cache
├── reports/                      # Timestamped matrix audit reports
├── dashboard.py                  # Real-time diagnostic metrics monitor
└── probe_daemon.py               # Autonomous background daemon
```

## Quick Start

### 1. Execute Matrix Shard Probe
```bash
python3 -m engines.probe_worker --shard-id 0 --total-shards 4 --max-batches 2
```

### 2. Launch Local Diagnostic Monitor
```bash
python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8080
```
Visit `http://localhost:8080` to inspect live telemetry signals and verification metrics.
