# Airline Operations Data Platform

An end-to-end data platform for airline on-time performance: ingestion from files and APIs, a layered warehouse with history tracking, data quality monitoring, a delay prediction model, and a secure REST API.

> Status: in progress. Ingestion, bronze, silver and gold layers complete.

## Architecture

```
Sources                    Warehouse (DuckDB)                       Consumers
---------                  -------------------------------------    -------------------
BTS monthly CSVs   ──┐     bronze   raw, as delivered + audit cols   Dashboard
OurAirports CSV    ──┼──►  silver   typed, cleaned, deduplicated  ►  ASP.NET Core API
OpenFlights file   ──┤     gold     facts, dimensions (SCD2)         Delay model
OpenSky API        ──┘     meta     load log, quality results
```

## Data sources

| Source | Type | What it gives |
|---|---|---|
| [BTS On-Time Performance](https://www.transtats.bts.gov/) | Monthly zipped CSV | Every US domestic flight: schedule, delays, cancellations, delay causes |
| [OurAirports](https://ourairports.com/data/) | CSV | Airport reference data |
| [OpenFlights](https://openflights.org/data) | CSV | Airline reference data |
| [OpenSky Network](https://opensky-network.org/) | REST API | Flight state data (planned) |

## Ingestion design

- **Retries with exponential backoff** on every download (2s, 4s, 8s, 16s).
- **Atomic downloads**: written to `.part` and renamed only when complete, so a crash never leaves a file that looks valid.
- **Safe re-runs**: each file is fingerprinted with SHA-256 and recorded in `meta.load_log`. Files already loaded are skipped. A changed file with the same name replaces its earlier rows.
- **Transactional loads**: each file loads inside a transaction, so a failure rolls back cleanly and is logged with its error.
- **Bronze keeps the source as delivered**: every column loaded as text, plus `_source_file`, `_file_hash`, `_loaded_at` for lineage.

## Warehouse layers

| Layer | Tables | Purpose |
|---|---|---|
| bronze | `flights`, `airports`, `airlines` | Raw files as delivered, all text, plus audit columns |
| silver | `stg_flights` | Typed, renamed, deduplicated on the business key |
| gold | `dim_airports`, `dim_airlines`, `fct_flights` | Star schema for analysis, API and modelling |

Key design decisions:
- **Airports**: only airports with an IATA code are kept, since flights can only join on that code (about 9,000 of 86,000).
- **Airlines**: the OpenFlights reference file was out of date (e.g. `9E` listed as Pinnacle Airlines, renamed Endeavor Air in 2013), so carriers are maintained as a dbt seed and tracked with an **SCD Type 2 snapshot**. A renamed airline gets a new version; the old one is closed, not overwritten.
- **Point-in-time join**: each flight links to the airline version valid on the flight date.
- **Data quality tests**: uniqueness and nulls on keys, accepted cancellation codes, arrival delay only missing for cancelled or diverted flights, exactly one current version per airline, and every flight airport present in `dim_airports`.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m ingestion.load_bronze --year 2024 --months 1 2 3
python -m ingestion.profile_bronze

cd transform
dbt build --profiles-dir .
```

Logs are written to `logs/ingestion.log`; the warehouse to `data/warehouse/airline.duckdb`.

## Roadmap

- [x] Ingestion with retries, logging and safe re-runs; bronze layer
- [x] dbt silver and gold models, business keys, SCD Type 2 dimensions
- [ ] Data quality tests, source reconciliation and alerting
- [ ] Prefect scheduling; pytest suite
- [ ] ASP.NET Core REST API with JWT auth, logging and xUnit tests
- [ ] Dashboard
- [ ] Delay prediction model with training/inference tables and drift monitoring

## Known limitations

- BTS covers US domestic carriers only.
- DuckDB is a single-node warehouse; the layer design would carry over to a cloud lakehouse.
