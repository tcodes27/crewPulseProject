from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def test_bitemporal_as_of_query_reconstructs_prior_and_corrected_knowledge():
    assert DATABASE_URL, "DATABASE_URL is missing from .env."

    sql_file = (
        PROJECT_ROOT / "sql" / "temporal_crew_assignment_queries.sql"
    ).read_text()

    query = sql_file.split(
        "-- 2. TWO-DIMENSIONAL AS-OF QUERY", 1
    )[1].split(
        "-- 3. ASSIGNMENT STATUS TIMELINE", 1
    )[0]

    timestamp_literal = (
        "TIMESTAMPTZ '2026-10-26 18:50:00-04'"
    )
    query = query.replace(
        timestamp_literal, ":effective_at", 1
    ).replace(
        timestamp_literal, ":known_at", 1
    )

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

                now = datetime.now(timezone.utc)
                correction_time = max(
                    now,
                    original["recorded_at"] + timedelta(seconds=2)
                )
                known_before = correction_time - timedelta(seconds=1)
                known_after = correction_time
                effective_at = original["effective_from"]

                corrected_status = "TEST_CORRECTED"

                conn.execute(text("""
                    UPDATE core.crew_assignment_history
                    SET recorded_to = :correction_time
                    WHERE history_id = :history_id
                """), {
                    "correction_time": correction_time,
                    "history_id": original["history_id"],
                })

                conn.execute(text("""
                    INSERT INTO core.crew_assignment_history (
                        assignment_id, crew_id, flight_id,
                        assignment_status, effective_from,
                        effective_to, recorded_at, recorded_to,
                        change_reason
                    )
                    VALUES (
                        :assignment_id, :crew_id, :flight_id,
                        :status, :effective_from,
                        :effective_to, :recorded_at, NULL,
                        'TEST ONLY: bitemporal as-of validation'
                    )
                """), {
                    "assignment_id": original["assignment_id"],
                    "crew_id": original["crew_id"],
                    "flight_id": original["flight_id"],
                    "status": corrected_status,
                    "effective_from": original["effective_from"],
                    "effective_to": original["effective_to"],
                    "recorded_at": correction_time,
                })

                before = conn.execute(
                    text(query),
                    {
                        "effective_at": effective_at,
                        "known_at": known_before,
                    },
                ).mappings().all()

                after = conn.execute(
                    text(query),
                    {
                        "effective_at": effective_at,
                        "known_at": known_after,
                    },
                ).mappings().all()

                before_match = [
                    row for row in before
                    if row["assignment_id"] == original["assignment_id"]
                ]
                after_match = [
                    row for row in after
                    if row["assignment_id"] == original["assignment_id"]
                ]

                assert len(before_match) == 1
                assert before_match[0]["assignment_status"] == (
                    original["assignment_status"]
                )

                assert len(after_match) == 1
                assert after_match[0]["assignment_status"] == (
                    corrected_status
                )

            finally:
                transaction.rollback()
    finally:
        engine.dispose()
