"""Load raw source files into the bronze layer.

Bronze rule: keep the source exactly as it arrived. Every column is
loaded as text (no type guessing, nothing dropped), and three audit
columns are added: _source_file, _file_hash, _loaded_at. Cleaning and
typing happen later in the silver layer (dbt, Day 2).

Usage:
    python -m ingestion.load_bronze --year 2024 --months 1 2 3
    python -m ingestion.load_bronze --year 2024 --months 1 --skip-download
"""
import argparse
import zipfile
from pathlib import Path

from ingestion import config
from ingestion.common import already_loaded, connect, download, file_hash, log, record_load


def load_file(con, source: str, csv_path: Path, table: str, read_options: str = "header=true") -> None:
    """Load one CSV into a bronze table, safely re-runnable."""
    digest = file_hash(csv_path)
    if already_loaded(con, digest, table):
        log.info("Skipping %s, already loaded into %s", csv_path.name, table)
        return

    src = str(csv_path).replace("'", "''")
    select = f"""
        SELECT *,
               '{csv_path.name}' AS _source_file,
               '{digest}'        AS _file_hash,
               current_timestamp AS _loaded_at
        FROM read_csv('{src}', all_varchar=true, {read_options})
    """
    try:
        con.execute("BEGIN TRANSACTION")
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='bronze' AND table_name=?",
            [table.split(".")[1]],
        ).fetchone()
        if exists:
            # Remove any earlier copy of this file (e.g. a corrected re-release), then insert
            con.execute(f"DELETE FROM {table} WHERE _source_file = ?", [csv_path.name])
            con.execute(f"INSERT INTO {table} BY NAME {select}")
        else:
            con.execute(f"CREATE TABLE {table} AS {select}")
        rows = con.execute(f"SELECT count(*) FROM {table} WHERE _file_hash = ?", [digest]).fetchone()[0]
        con.execute("COMMIT")
        record_load(con, source, csv_path.name, digest, table, rows, "success")
        log.info("Loaded %s rows from %s into %s", f"{rows:,}", csv_path.name, table)
    except Exception as exc:
        con.execute("ROLLBACK")
        record_load(con, source, csv_path.name, digest, table, 0, "failed", str(exc)[:500])
        log.error("Failed loading %s: %s", csv_path.name, exc)
        raise


def load_bts_month(con, year: int, month: int, skip_download: bool) -> None:
    zip_path = config.RAW_DIR / "bts" / f"bts_{year}_{month:02d}.zip"
    if not skip_download:
        download(config.BTS_URL.format(year=year, month=month), zip_path)
    if not zip_path.exists():
        log.error("Missing %s. Download it or drop --skip-download.", zip_path.name)
        return

    extract_dir = zip_path.with_suffix("")
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        zf.extractall(extract_dir, members=csv_names)

    for name in csv_names:
        # Rename to a stable name so the load log and audit columns stay readable
        src = extract_dir / name
        stable = extract_dir / f"bts_{year}_{month:02d}.csv"
        src.replace(stable)
        load_file(con, "bts", stable, "bronze.flights")


def load_reference(con, skip_download: bool) -> None:
    airports = config.RAW_DIR / "reference" / "airports.csv"
    airlines = config.RAW_DIR / "reference" / "airlines.dat"
    if not skip_download:
        download(config.AIRPORTS_URL, airports)
        download(config.AIRLINES_URL, airlines)

    if airports.exists():
        load_file(con, "ourairports", airports, "bronze.airports")
    if airlines.exists():
        # OpenFlights file has no header and uses \N for nulls
        cols = ", ".join(f"'{c}': 'VARCHAR'" for c in config.AIRLINES_COLUMNS)
        load_file(con, "openflights", airlines, "bronze.airlines",
                  read_options=f"header=false, nullstr='\\N', columns={{{cols}}}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load raw files into the bronze layer")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True)
    parser.add_argument("--skip-download", action="store_true", help="use files already in data/raw")
    args = parser.parse_args()

    con = connect()
    try:
        load_reference(con, args.skip_download)
        for month in args.months:
            load_bts_month(con, args.year, month, args.skip_download)
    finally:
        con.close()


if __name__ == "__main__":
    main()
