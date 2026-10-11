from ingestion.common import file_hash


def test_same_content_gives_same_hash(tmp_path):
    file_a = tmp_path / "a.csv"                  # make a file path in a temporary folder
    file_a.write_text("flight,delay\nAA100,5\n") # put some content in it

    first = file_hash(file_a)    # fingerprint it once
    second = file_hash(file_a)   # fingerprint it again

    assert first == second       # check: both fingerprints must match


def test_different_content_gives_different_hash(tmp_path):
    file_a = tmp_path/"a.csv"
    file_a.write_text("flight,delay\nAA100,10")
    file_b= tmp_path/"b.csv"
    file_b.write_text("flight,delay\nAA100, 15")

    first=file_hash(file_a)
    second = file_hash(file_b)

    assert first != second
    # 1. write two files with different content
    # 2. hash both
    # 3. assert the hashes are NOT equal
    