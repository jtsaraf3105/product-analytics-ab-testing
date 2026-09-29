# Runbook

```bash
make install          # Python 3.12 venv + requirements.txt
make all              # data → sql → model → notebook → dashboard (~5 min on a laptop)
make test             # 18 tests
open dashboard/index.html
jupyter lab notebooks/ab_test.ipynb
```

Individual steps:

| Command | Output |
|---|---|
| `make data` | `data/raw/ga4/events_YYYYMMDD.parquet` (92 shards, 95 MB) + `GROUND_TRUTH.json` |
| `make sql` | `data/processed/NN_*.csv` |
| `python -m analytics.run_sql --only 06_cohort_retention` | one query |
| `python -m analytics.run_sql --show-duckdb 08_experiment_extract` | the transpiled DuckDB SQL |
| `make model` | `powerbi/data/*.csv` star schema |
| `make notebook` | re-executes `notebooks/ab_test.ipynb` from `ab_test.py` |
| `make dashboard` | `dashboard/index.html` (`#0`…`#3` deep-link pages) |

## Running on the real GA4 dataset (BigQuery)
1. Create a GCP project (the free sandbox is enough) and open the BigQuery console.
2. `make bigquery Q=04_funnel` prints the query. Paste it and run. The table name already points at
   `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`.
3. `08_experiment_extract.sql` returns no rows on real data (the experiment is simulated). The KPI,
   funnel, cohort and RFM queries work as-is.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `FileNotFoundError: data/processed/...` | Run `make data sql` first. |
| Dashboard charts blank | It loads plotly.js from a CDN, so an internet connection is needed. |
| Notebook can't import `analytics` | Run it from the repo root or `notebooks/` (it adds the root to `sys.path`). |
