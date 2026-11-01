import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def test_bitemporal_audit_detects_overlapping_versions():
    assert DATABASE_URL, "DATABASE_URL is missing from .env."
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                original = conn.execute(text("""
                    SELECT *
                    FROM core.crew_assignment_history
                    WHERE recorded_to IS NULL
                      AND effective_to IS NULL
                    ORDER BY history_id
                    LIMIT 1
                """)).mappings().one()

                conn.execute(text("""
                    INSERT INTO core.crew_assignment_history (
                        assignment_id, crew_id, flight_id,
                        assignment_status, effective_from,
                        effective_to, recorded_at, recorded_to,
                        change_reason
                    )
                    VALUES (
                        :assignment_id, :crew_id, :flight_id,
                        :status, :effective_from, NULL,
                        :recorded_at, NULL,
                        'TEST ONLY: deliberate temporal overlap'
                    )
                """), {
                    "assignment_id": original["assignment_id"],
                    "crew_id": original["crew_id"],
                    "flight_id": original["flight_id"],
                    "status": original["assignment_status"],
                    "effective_from": original["effective_from"],
                    "recorded_at": original["recorded_at"],
                })
                audit_sql = (
                    PROJECT_ROOT / "sql" / "bitemporal_audit_queries.sql"
                ).read_text()

                findings = conn.execute(
                    text(audit_sql)
                ).mappings().all()

                matching = [
                    row for row in findings
                    if row["assignment_id"] == original["assignment_id"]
                ]

                assert len(matching) == 1, (
                    "Audit should detect the deliberately overlapping versions."
                )

            finally:
                transaction.rollback()
    finally:
        engine.dispose()
