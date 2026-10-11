"""Quick sanity profile of the bronze layer after a load.

Run: python -m ingestion.profile_bronze
Use what this prints to decide the cleaning rules for silver (Day 2).
"""
from ingestion.common import connect


def main() -> None:
    con = connect()
    print("\n== Load log ==")
    print(con.sql("""
        SELECT source, file_name, target_table, row_count, status, loaded_at
        FROM meta.load_log ORDER BY loaded_at
    """))

    print("\n== Rows per bronze table ==")
    for (t,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='bronze' ORDER BY 1"
    ).fetchall():
        n = con.execute(f"SELECT count(*) FROM bronze.{t}").fetchone()[0]
        print(f"bronze.{t:<10} {n:>12,}")

    tables = {r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='bronze'").fetchall()}
    if "flights" in tables:
        print("\n== Flights: quick checks ==")
        print(con.sql("""
            SELECT
                count(*)                                              AS flights,
                count(DISTINCT Reporting_Airline)                     AS carriers,
                count(DISTINCT Origin)                                AS origin_airports,
                min(FlightDate)                                       AS first_date,
                max(FlightDate)                                       AS last_date,
                round(avg(TRY_CAST(Cancelled AS DOUBLE)) * 100, 2)    AS cancelled_pct,
                round(avg(TRY_CAST(ArrDelay AS DOUBLE)), 1)           AS avg_arr_delay_min,
                sum(CASE WHEN ArrDelay IS NULL OR ArrDelay = '' THEN 1 ELSE 0 END) AS missing_arr_delay
            FROM bronze.flights
        """))
        print("\n== Possible duplicates on the business key ==")
        print(con.sql("""
            SELECT count(*) AS duplicate_keys FROM (
                SELECT FlightDate, Reporting_Airline, Flight_Number_Reporting_Airline,
                       Origin, Dest, CRSDepTime
                FROM bronze.flights
                GROUP BY ALL HAVING count(*) > 1
            )
        """))
    con.close()


if __name__ == "__main__":
    main()
