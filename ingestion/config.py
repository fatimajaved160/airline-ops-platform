"""Central configuration: paths and source URLs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE_PATH = ROOT / "data" / "warehouse" / "airline.duckdb"
LOG_DIR = ROOT / "logs"

# US Bureau of Transportation Statistics, On-Time Performance (one zip per month)
BTS_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

# Reference data
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
AIRLINES_COLUMNS = [
    "airline_id", "name", "alias", "iata", "icao", "callsign", "country", "active",
]

# Download behaviour
MAX_RETRIES = 4
BACKOFF_SECONDS = 2  # doubles on every retry: 2, 4, 8, 16
TIMEOUT_SECONDS = 120
