from ingestion import config
from ingestion.common import connect
from ingestion.load_bronze import load_file


def test_loading_same_file_twice_does_not_duplicate(tmp_path, monkeypatch):
    # Setup: use a throwaway database instead of the real one
    monkeypatch.setattr(config, "WAREHOUSE_PATH", tmp_path / "test.duckdb")
    con = connect()



    # 1. Create a small CSV file with a header and 2 flight rows
    #    (same as before: a path in tmp_path, then .write_text(...))
    file_a = tmp_path/"a.csv"
    file_a.write_text("flight,delay\nAA100,10\nAA200,5\n")

    # 2. Load it into "bronze.flights" TWICE, like this:
    #    load_file(con, "test", <your file>, "bronze.flights")
    load_file(con, "test",file_a,"bronze.flights")
    load_file(con, "test",file_a,"bronze.flights")



    # 3. Count the rows in bronze.flights. You know this SQL:
    rows=con.execute("select count(*) from bronze.flights").fetchone()[0]
    #    rows = con.execute("<your SQL>").fetchone()[0]

    # 4. Assert the count is what it SHOULD be if there are no duplicates
    assert rows == 2