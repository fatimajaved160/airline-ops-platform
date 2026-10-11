"""Shared helpers: logging, downloads with retries, and the load log.

The load log (meta.load_log) is what makes every load safe to re-run:
a file whose content hash has already loaded successfully is skipped,
and a failed or partial load is cleaned up and retried next run.
"""
import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import requests

from ingestion import config


def get_logger(name: str) -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        for handler in (logging.StreamHandler(), logging.FileHandler(config.LOG_DIR / "ingestion.log")):
            handler.setFormatter(fmt)
            logger.addHandler(handler)
    return logger


log = get_logger("ingestion")


def download(url: str, dest: Path) -> Path:
    """Download url to dest with retries and exponential backoff.

    Writes to a .part file first and renames only when complete, so a
    crash mid-download never leaves a half-written file that looks valid.
    """
    if dest.exists():
        log.info("Already downloaded, skipping: %s", dest.name)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    wait = config.BACKOFF_SECONDS

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            log.info("Downloading %s (attempt %d/%d)", url, attempt, config.MAX_RETRIES)
            with requests.get(url, stream=True, timeout=config.TIMEOUT_SECONDS) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            tmp.rename(dest)
            log.info("Saved %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
            return dest
        except requests.RequestException as exc:
            log.warning("Download failed: %s", exc)
            tmp.unlink(missing_ok=True)
            if attempt == config.MAX_RETRIES:
                raise
            log.info("Retrying in %ds", wait)
            time.sleep(wait)
            wait *= 2


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def connect() -> duckdb.DuckDBPyConnection:
    config.WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.WAREHOUSE_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS meta.load_log (
            source       VARCHAR,
            file_name    VARCHAR,
            file_hash    VARCHAR,
            target_table VARCHAR,
            row_count    BIGINT,
            status       VARCHAR,   -- 'success' or 'failed'
            error        VARCHAR,
            loaded_at    TIMESTAMP
        )
        """
    )
    return con


def already_loaded(con, digest: str, target_table: str) -> bool:
    return con.execute(
        "SELECT 1 FROM meta.load_log WHERE file_hash = ? AND target_table = ? AND status = 'success'",
        [digest, target_table],
    ).fetchone() is not None


def record_load(con, source, file_name, digest, target_table, rows, status, error=None):
    con.execute(
        "INSERT INTO meta.load_log VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [source, file_name, digest, target_table, rows, status, error,
         datetime.now(timezone.utc).replace(tzinfo=None)],
    )
