"""Run the whole pipeline in order, record every run, and alert on failure.

Usage:
    python -m pipeline.run_pipeline --year 2024 --months 1
"""
import argparse
import subprocess
import sys
import uuid
from datetime import datetime, timezone

from ingestion import config
from ingestion.common import connect, log


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def run_step(name, command, cwd=None):
    """Run one step as a command. Raise an error if it fails."""
    log.info("Step started: %s", name)
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed:\n{result.stdout[-1500:]}\n{result.stderr[-1500:]}")
    log.info("Step finished: %s", name)


def record_run(run_id, started_at, status, failed_step=None, error=None):
    con = connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
            run_id VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
            status VARCHAR, failed_step VARCHAR, error VARCHAR
        )
    """)
    con.execute("INSERT INTO meta.pipeline_runs VALUES (?, ?, ?, ?, ?, ?)",
                [run_id, started_at, now(), status, failed_step, (error or "")[:2000]])
    con.close()


def send_alert(run_id, failed_step, error):
    """Write the alert where a person will see it."""
    alert_file = config.LOG_DIR / "ALERTS.log"
    with open(alert_file, "a", encoding="utf-8") as f:
        f.write(f"{now():%Y-%m-%d %H:%M} | run {run_id} | FAILED at: {failed_step}\n{error}\n{'-' * 60}\n")
    log.error("ALERT: pipeline failed at %s. Details in %s", failed_step, alert_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    run_id = uuid.uuid4().hex[:8]
    started_at = now()
    py = sys.executable
    months = [str(m) for m in args.months]

    # The steps, in the order they must run. Each step is: (name, command, folder to run it in)
    load_command = [py, "-m", "ingestion.load_bronze", "--year", str(args.year), "--months", *months]
    if args.skip_download:
        load_command.append("--skip-download")
    dbt_command = ["dbt", "build", "--profiles-dir", "."]

    steps = [
        ("load bronze", load_command, None),
        ("dbt build",   dbt_command,  config.ROOT / "transform"),
    ]

    current = None
    try:
        for name, command, cwd in steps:
            current = name
            run_step(name, command, cwd)
    except Exception as exc:
        record_run(run_id, started_at, "failed", current, str(exc))
        send_alert(run_id, current, str(exc))
        # TODO 2: a step failed. Do two things:
        #   - record this run as failed, using record_run(...)
        #     (look at how the success case calls it below, and at the function's arguments above)
        #   - raise an alert, using send_alert(...)
        sys.exit(1)  # exit with an error code so Task Scheduler also knows it failed

    record_run(run_id, started_at, "success")
    log.info("Pipeline run %s succeeded", run_id)


if __name__ == "__main__":
    main()
