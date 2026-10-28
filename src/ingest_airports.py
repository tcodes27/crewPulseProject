import os
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from src.airport_transforms import prepare_airport_records
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

AIRPORTS_URL = "https://ourairports.com/data/airports.csv"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "airports.csv"
PIPELINE_NAME = "airport_reference_ingestion"

def download_airports():
    """Download the airport source data."""
    return pd.read_csv(AIRPORTS_URL, low_memory=False)


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from .env")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url)
    # Start and persist the monitoring record first.
    with engine.begin() as connection:
        run_id = connection.execute(
            text("""
                INSERT INTO ops.pipeline_runs (pipeline_name)
                VALUES (:name)
                RETURNING run_id
            """),
            {"name": PIPELINE_NAME},
        ).scalar_one()

    records_read = 0
    records_loaded = 0
    records_rejected = 0

    try:
        print(f"Pipeline run {run_id}: downloading airport data...")
        airports = download_airports()
        airports.to_csv(RAW_FILE, index=False)
        records_read = len(airports)
        selected, metrics = prepare_airport_records(airports)
        records_read = metrics["records_read"]
        records_loaded = metrics["records_loaded"]
        records_rejected = metrics["records_rejected"]

        invalid_iata_count = metrics["invalid_iata_count"]
        duplicate_count = metrics["duplicate_count"]
        missing_required_count = metrics["missing_required_count"]
        checks = [
            {
                "table_name": "core.airports",
                "check_name": "source_not_empty",
                "failed_records": int(records_read == 0),
                "check_status": (
                    "PASS" if records_read > 0 else "FAIL"
                ),
		"details": f"Source rows downloaded: {records_read}",
            },
            {
                "table_name": "core.airports",
                "check_name": "iata_code_eligibility",
                "failed_records": 0,
                "check_status": "PASS",
                "details": (
                    f"Eligible airport records: {records_loaded}; "
                    f"records excluded for missing or invalid IATA codes: "
                    f"{invalid_iata_count}."
                ),
            },
            {
                "table_name": "core.airports",
                "check_name": "duplicate_iata_codes",
                "failed_records": duplicate_count,
                "check_status": (
                    "PASS" if duplicate_count == 0 else "WARNING"
                ),
                "details": (
                    "Duplicate codes are removed before loading."
                ),
            },
            {
                "table_name": "core.airports",
                "check_name": "required_fields_present",
                "failed_records": missing_required_count,
                "check_status": (
                    "PASS" if missing_required_count == 0 else "WARNING"
                ),
                "details": (
                    "Airport code and airport name are required."
                ),
            },
        ]

        if records_read == 0 or records_loaded == 0:
            raise ValueError("No usable airport records were found.")

        print(f"Downloaded: {records_read:,}")
        print(f"Selected for loading: {records_loaded:,}")
        print(f"Excluded by filters: {records_rejected:,}")

        # Load airport data, quality results, and run outcome together.
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO core.airports
                        (airport_code, airport_name, city, country)
                    VALUES
                        (:airport_code, :airport_name, :city, :country)
                    ON CONFLICT (airport_code) DO UPDATE SET
                        airport_name = EXCLUDED.airport_name,
                        city = EXCLUDED.city,
                        country = EXCLUDED.country
                """),
                selected.to_dict(orient="records"),
            )

            for check in checks:
                connection.execute(
                    text("""
                        INSERT INTO ops.data_quality_results
                            (run_id, table_name, check_name,
                             failed_records, check_status, details)
                        VALUES
                            (:run_id, :table_name, :check_name,
                             :failed_records, :check_status, :details)
                    """),
                    {"run_id": run_id, **check},
                )

            connection.execute(
                text("""
                    UPDATE ops.pipeline_runs
                    SET finished_at = :finished,
                        run_status = 'SUCCESS',
                        records_read = :read,
                        records_inserted = :loaded,
                        records_rejected = :rejected
                    WHERE run_id = :run_id
                """),
                {
                    "finished": datetime.now(timezone.utc),
                    "read": records_read,
                    "loaded": records_loaded,
                    "rejected": records_rejected,
                    "run_id": run_id,
                },
            )

        print(f"Pipeline run {run_id} completed successfully.")
        print("Monitoring and data quality results recorded.")

    except Exception as error:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE ops.pipeline_runs
                    SET finished_at = :finished,
                        run_status = 'FAILED',
                        records_read = :read,
                        records_inserted = :loaded,
                        records_rejected = :rejected,
                        error_message = :error
                    WHERE run_id = :run_id
                """),
                {
                    "finished": datetime.now(timezone.utc),
                    "read": records_read,
                    "loaded": records_loaded,
                    "rejected": records_rejected,
                    "error": str(error)[:4000],
                    "run_id": run_id,
                },
            )

        print(f"Pipeline run {run_id} FAILED: {error}")
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
