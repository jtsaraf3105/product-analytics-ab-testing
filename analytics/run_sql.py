"""Run the BigQuery SQL in `sql/` locally on DuckDB, or print it for BigQuery.

The .sql files are written in **BigQuery Standard SQL** against the real public dataset
`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`. Locally we:
  1. point that table at a DuckDB view over the Parquet shards (with a `_TABLE_SUFFIX` column,
     exactly like BigQuery's wildcard tables),
  2. transpile BigQuery -> DuckDB with sqlglot,
  3. apply one rewrite sqlglot doesn't do: GA4's
     `(SELECT ... FROM UNNEST(event_params) WHERE key=..)` needs DuckDB's
     `UNNEST(..., max_depth := 2)` so the struct fields become columns.

    python -m analytics.run_sql                    # all queries -> data/processed/*.csv
    python -m analytics.run_sql --only 04_funnel   # one query
    python -m analytics.run_sql --show-duckdb 04_funnel
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import duckdb
import pandas as pd
import sqlglot

GA4_TABLE = "`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`"
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
_UNNEST_SUBQUERY = re.compile(r"FROM UNNEST\(([\w.]+)\)(?!\s+AS)")


def to_duckdb(bigquery_sql: str) -> str:
    sql = bigquery_sql.replace(GA4_TABLE, "events")
    out = sqlglot.transpile(sql, read="bigquery", write="duckdb", pretty=True)[0]
    return _UNNEST_SUBQUERY.sub(r"FROM (SELECT UNNEST(\1, max_depth := 2))", out)


def connect(raw_dir: str | Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    glob = str(Path(raw_dir) / "events_*.parquet")
    con.execute(
        f"CREATE VIEW events AS SELECT *, event_date AS _TABLE_SUFFIX FROM read_parquet('{glob}')"
    )
    return con


def run_query(con: duckdb.DuckDBPyConnection, path: Path) -> pd.DataFrame:
    return con.execute(to_duckdb(path.read_text())).df()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/ga4")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--only", default=None, help="run a single query by file stem")
    ap.add_argument("--show-duckdb", default=None, help="print the transpiled SQL and exit")
    a = ap.parse_args()
    if a.show_duckdb:
        print(to_duckdb((SQL_DIR / f"{a.show_duckdb}.sql").read_text()))
        return
    con = connect(a.raw)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for path in sorted(SQL_DIR.glob("*.sql")):
        if a.only and path.stem != a.only:
            continue
        t0 = time.perf_counter()
        df = run_query(con, path)
        df.to_csv(out / f"{path.stem}.csv", index=False)
        print(f"{path.stem:28s} {len(df):>8,} rows  {time.perf_counter() - t0:5.1f}s")


if __name__ == "__main__":
    main()
