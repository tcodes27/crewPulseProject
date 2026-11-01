import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from record_assignment_history import sync_assignment_history

DATABASE_URL = os.getenv("DATABASE_URL")


def test_status_change_preserves_system_time_and_prevents_duplicates():
    assert DATABASE_URL, "DATABASE_URL is missing from .env."

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            transaction = conn.begin()

            try:
                assignment = conn.execute(text("""
                    SELECT
                        ca.assignment_id,
                        ca.assignment_status,
                        h.history_id
                    FROM core.crew_assignments ca
                    JOIN LATERAL (
                        SELECT history_id, assignment_status
                        FROM core.crew_assignment_history
                        WHERE assignment_id = ca.assignment_id
                        ORDER BY effective_from DESC, history_id DESC
                        LIMIT 1
                    ) h ON TRUE
                    WHERE ca.assignment_status = h.assignment_status
                    ORDER BY ca.assignment_id
                    LIMIT 1;
                """)).mappings().one()

                new_status = (
                    "CONFIRMED"
                    if assignment["assignment_status"] != "CONFIRMED"
                    else "ASSIGNED"
                )

                conn.execute(text("""
                    UPDATE core.crew_assignments
                    SET assignment_status = :status
                    WHERE assignment_id = :assignment_id;
                """), {
                    "status": new_status,
                    "assignment_id": assignment["assignment_id"],
                })

                assert sync_assignment_history(conn) == (0, 1)

                previous = conn.execute(text("""
                    SELECT effective_to, recorded_to
                    FROM core.crew_assignment_history
                    WHERE history_id = :history_id;
                """), {
                    "history_id": assignment["history_id"],
                }).mappings().one()

                assert previous["effective_to"] is not None
                assert previous["recorded_to"] is None

                current = conn.execute(text("""
                    SELECT assignment_status, effective_to, recorded_to
                    FROM core.crew_assignment_history
                    WHERE assignment_id = :assignment_id
                    ORDER BY effective_from DESC, history_id DESC
                    LIMIT 1;
                """), {
                    "assignment_id": assignment["assignment_id"],
                }).mappings().one()

                assert current["assignment_status"] == new_status
                assert current["effective_to"] is None
                assert current["recorded_to"] is None

                count_before = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM core.crew_assignment_history
                    WHERE assignment_id = :assignment_id;
                """), {
                    "assignment_id": assignment["assignment_id"],
                }).scalar_one()

                assert sync_assignment_history(conn) == (0, 0)

                count_after = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM core.crew_assignment_history
                    WHERE assignment_id = :assignment_id;
                """), {
                    "assignment_id": assignment["assignment_id"],
                }).scalar_one()

                assert count_after == count_before

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
