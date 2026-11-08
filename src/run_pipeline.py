import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from the project .env file.")

PIPELINE_NAME = "crew_pulse_end_to_end"

PIPELINE_STEPS = [
    ("Airport ingestion", "ingest_airports.py"),
    ("Synthetic operations data", "generate_operations_data.py"),
    ("Assignment history synchronization", "record_assignment_history.py"),
    ("Data quality checks", "run_data_quality_checks.py"),
]


def run_pipeline():
    engine = create_engine(DATABASE_URL)
    run_id = None

    try:
        with engine.begin() as conn:
            run_id = conn.execute(
                text("""
                    INSERT INTO ops.pipeline_runs (pipeline_name)
                    VALUES (:pipeline_name)
                    RETURNING run_id
                """),
                {"pipeline_name": PIPELINE_NAME},
            ).scalar_one()

        print(f"\nCrewPulse pipeline started. Run ID: {run_id}")

        for step_name, script_name in PIPELINE_STEPS:
            print(f"\n--- {step_name} ---")

            subprocess.run(
                [sys.executable, "-m", f"src.{Path(script_name).stem}"],
                cwd=PROJECT_ROOT,
                check=True,
            )

            print(f"Completed: {step_name}")

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE ops.pipeline_runs
                    SET finished_at = CURRENT_TIMESTAMP,
                        run_status = 'SUCCESS'
                    WHERE run_id = :run_id
                """),
                {"run_id": run_id},
            )

        print(f"\nPipeline completed successfully. Run ID: {run_id}")

    except Exception as error:
        if run_id is not None:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE ops.pipeline_runs
                        SET finished_at = CURRENT_TIMESTAMP,
                            run_status = 'FAILED',
                            error_message = :error_message
                        WHERE run_id = :run_id
                    """),
                    {
                        "run_id": run_id,
                        "error_message": str(error)[:2000],
                    },
                )

        print(f"\nPipeline failed: {error}")
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    run_pipeline()
