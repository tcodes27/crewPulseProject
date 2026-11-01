import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from correct_assignment_history import correct_assignment_history

DATABASE_URL = os.getenv("DATABASE_URL")


def test_retroactive_correction_preserves_both_time_periods():
    assert DATABASE_URL, "DATABASE_URL is missing from .env."
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()

            try:
                original = conn.execute(text("""
                    SELECT history_id, assignment_status,
                           effective_from, effective_to
                    FROM core.crew_assignment_history
                    WHERE recorded_to IS NULL
                    ORDER BY history_id
                    LIMIT 1
                """)).mappings().one()

                corrected_status = (
                    "CONFIRMED"
                    if original["assignment_status"] != "CONFIRMED"
                    else "ASSIGNED"
                )

                new_id = correct_assignment_history(
                    conn,
                    original["history_id"],
                    corrected_status,
                    "Integration test: simulated retroactive correction",
                )

                old_record = conn.execute(text("""
                    SELECT recorded_at, recorded_to,
                           effective_from, effective_to
                    FROM core.crew_assignment_history
                    WHERE history_id = :history_id
                """), {
                    "history_id": original["history_id"]
                }).mappings().one()

                new_record = conn.execute(text("""
                    SELECT assignment_status, recorded_at,
                           recorded_to, effective_from, effective_to
                    FROM core.crew_assignment_history
                    WHERE history_id = :history_id
                """), {
                    "history_id": new_id
                }).mappings().one()

                assert old_record["recorded_to"] is not None
                assert old_record["recorded_to"] == new_record["recorded_at"]
                assert new_record["assignment_status"] == corrected_status
                assert new_record["recorded_to"] is None
                assert new_record["effective_from"] == original["effective_from"]
                assert new_record["effective_to"] == original["effective_to"]

                with pytest.raises(ValueError):
                    correct_assignment_history(
                        conn,
                        original["history_id"],
                        "ASSIGNED",
                        "Attempt to correct an already superseded version",
                    )

            finally:
                transaction.rollback()
    finally:
        engine.dispose()
