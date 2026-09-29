PY ?= .venv/bin/python
.PHONY: install data sql model notebook dashboard all test lint bigquery

install:     ## venv + pinned requirements
	python3.12 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt

data:        ## simulate the GA4-schema export (4.26M events, seeded) -> data/raw/ga4
	$(PY) -m simulate.generate_ga4 --out data/raw/ga4 --users-per-day 5000 --seed 42

sql:         ## run every BigQuery SQL file on DuckDB -> data/processed/*.csv
	$(PY) -m analytics.run_sql

model:       ## Power BI star schema CSVs -> powerbi/data/
	$(PY) -m analytics.build_model

notebook:    ## rebuild + execute the A/B notebook from its .py source
	cd notebooks && ../.venv/bin/jupytext --to ipynb ab_test.py -o ab_test.ipynb -q && \
	../.venv/bin/jupyter nbconvert --to notebook --execute --inplace ab_test.ipynb

dashboard:   ## dashboard/index.html (Plotly, 4 pages)
	$(PY) -m analytics.build_dashboard

all: data sql model notebook dashboard   ## everything, from scratch (~5 min)

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check . && $(PY) -m ruff format --check .

bigquery:    ## print a query for the BigQuery console (real GA4 data): make bigquery Q=04_funnel
	@cat sql/$(Q).sql
