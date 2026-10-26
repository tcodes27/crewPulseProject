
import os
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from .env")

AIRPORTS_URL = "https://ourairports.com/data/airports.csv"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "airports.csv"
PIPELINE_NAME = "airport_reference_ingestion"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(DATABASE_URL)

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

        airports = pd.read_csv(AIRPORTS_URL, low_memory=False)
        airports.to_csv(RAW_FILE, index=False)
        records_read = len(airports)

        required_source_columns = [
            "iata_code", "name", "municipality", "iso_country"
        ]
        missing_columns = [
            column for column in required_source_columns
            if column not in airports.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Source data is missing columns: {missing_columns}"
            )

        # Keep records with a valid three-letter IATA airport code.
        valid_code = airports["iata_code"].str.fullmatch(
            r"[A-Z]{3}", na=False
        )
        selected = airports[valid_code].copy()
        records_rejected = records_read - len(selected)

        duplicate_count = int(
            selected["iata_code"].duplicated().sum()
        )

        selected = selected[
            required_source_columns
        ].rename(
            columns={
                "iata_code": "airport_code",
                "name": "airport_name",
                "municipality": "city",
                "iso_country": "country",
            }
        )

        selected = selected.drop_duplicates(
            subset=["airport_code"]
        )

        # Required fields must be present before loading.
        missing_required = (
            selected["airport_code"].isna()
            | selected["airport_name"].isna()
            | selected["airport_name"].astype(str).str.strip().eq("")
        )
        missing_required_count = int(missing_required.sum())
        selected = selected[~missing_required].copy()

        selected = selected.astype(object).where(
            pd.notna(selected), None
        )
        records_loaded = len(selected)

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
                "check_name": "valid_iata_codes",
                "failed_records": records_rejected,
                "check_status": (
                    "PASS" if records_rejected == 0 else "WARNING"
                ),
                "details": (
                    "Rows without a three-letter IATA code are excluded "
                    "by design."
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
