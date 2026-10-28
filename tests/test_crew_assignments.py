
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def test_every_flight_has_two_crew_assignments():
    """Verify every flight has exactly two crew assignments."""

    assert DATABASE_URL, "DATABASE_URL is missing from the .env file."

    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT f.flight_id, COUNT(ca.assignment_id) AS crew_count
                FROM core.flights AS f
                LEFT JOIN core.crew_assignments AS ca
                    ON f.flight_id = ca.flight_id
                GROUP BY f.flight_id
                HAVING COUNT(ca.assignment_id) <> 2;
            """))

            flights_with_wrong_crew_count = result.fetchall()

        assert flights_with_wrong_crew_count == [], (
            "Flights without exactly two crew assignments: "
            f"{flights_with_wrong_crew_count}"
        )
    finally:
        engine.dispose()
def test_no_duplicate_crew_assignments_per_flight():
    """Verify a crew member is not assigned to the same flight twice."""
    assert DATABASE_URL, "DATABASE_URL is missing from the .env file."

    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT flight_id, crew_id, COUNT(*) AS duplicate_count
                FROM core.crew_assignments
                GROUP BY flight_id, crew_id
                HAVING COUNT(*) > 1;
            """))
            duplicates = result.fetchall()

        assert duplicates == [], (
            f"Duplicate crew assignments found: {duplicates}"
        )
    finally:
        engine.dispose()
def test_every_assignment_references_existing_records():
    """Verify each assignment points to an existing flight and crew member."""
    assert DATABASE_URL, "DATABASE_URL is missing from the .env file."

    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT ca.assignment_id
                FROM core.crew_assignments AS ca
                LEFT JOIN core.flights AS f
                    ON ca.flight_id = f.flight_id
                LEFT JOIN core.crew_members AS cm
                    ON ca.crew_id = cm.crew_id
                WHERE f.flight_id IS NULL
                   OR cm.crew_id IS NULL;
            """))
            invalid_assignments = result.fetchall()

        assert invalid_assignments == [], (
            f"Assignments with missing flight or crew records: "
            f"{invalid_assignments}"
        )
    finally:

        engine.dispose()
def test_every_assignment_has_one_current_history_record():
    """Verify each assignment has exactly one open history record."""
    assert DATABASE_URL, "DATABASE_URL is missing from the .env file."

    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT
                    ca.assignment_id,
                    COUNT(h.history_id) AS current_record_count
                FROM core.crew_assignments AS ca
                LEFT JOIN core.crew_assignment_history AS h
                    ON ca.assignment_id = h.assignment_id
                    AND h.effective_to IS NULL
                GROUP BY ca.assignment_id
                HAVING COUNT(h.history_id) <> 1;
            """))
            invalid_assignments = result.fetchall()

        assert invalid_assignments == [], (
            "Assignments without exactly one current history record: "
            f"{invalid_assignments}"
        )
    finally:
        engine.dispose()
