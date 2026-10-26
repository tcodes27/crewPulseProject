
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing. Check your .env file.")

engine = create_engine(DATABASE_URL)


def sync_assignment_history(conn):
    """Record new assignments and changes to existing assignment statuses."""
    run_time = datetime.now(timezone.utc)

    # Find assignments whose current status differs from the latest history.
    changed_assignments = conn.execute(
        text("""
            SELECT
                ca.assignment_id,
                ca.crew_id,
                ca.flight_id,
                ca.assignment_status,
                h.history_id,
                h.assignment_status AS previous_status
            FROM core.crew_assignments AS ca
            JOIN LATERAL (
                SELECT
                    history_id,
                    assignment_status
                FROM core.crew_assignment_history
                WHERE assignment_id = ca.assignment_id
                ORDER BY effective_from DESC, history_id DESC
                LIMIT 1
            ) AS h ON TRUE
            WHERE ca.assignment_status
                  IS DISTINCT FROM h.assignment_status
            FOR UPDATE OF ca
        """)
    ).mappings().all()

    updated_count = 0

    for assignment in changed_assignments:
        # Close the previous open history entry.
        conn.execute(
            text("""
                UPDATE core.crew_assignment_history
                SET effective_to = :run_time
                WHERE history_id = :history_id
                  AND effective_to IS NULL
            """),
            {
                "run_time": run_time,
                "history_id": assignment["history_id"],
            },
        )

        # Insert the new state.
        conn.execute(
            text("""
                INSERT INTO core.crew_assignment_history (
                    assignment_id,
                    crew_id,
                    flight_id,
                    assignment_status,
                    effective_from,
                    change_reason
                )
                VALUES (
                    :assignment_id,
                    :crew_id,
                    :flight_id,
                    :assignment_status,
                    :effective_from,
                    :change_reason
                )
            """),
            {
                "assignment_id": assignment["assignment_id"],
                "crew_id": assignment["crew_id"],
                "flight_id": assignment["flight_id"],
                "assignment_status": assignment["assignment_status"],
                "effective_from": run_time,
                "change_reason": (
                    "Status changed from "
                    f"{assignment['previous_status']} to "
                    f"{assignment['assignment_status']}"
                ),
            },
        )

        updated_count += 1

    # Record any assignments that have never had a history entry.
    new_result = conn.execute(
        text("""
            INSERT INTO core.crew_assignment_history (
                assignment_id,
                crew_id,
                flight_id,
                assignment_status,
                effective_from,
                change_reason
            )
            SELECT
                ca.assignment_id,
                ca.crew_id,
                ca.flight_id,
                ca.assignment_status,
                COALESCE(ca.assigned_at, :run_time),
                'Initial assignment history'
            FROM core.crew_assignments AS ca
            WHERE NOT EXISTS (
                SELECT 1
                FROM core.crew_assignment_history AS h
                WHERE h.assignment_id = ca.assignment_id
            )
            RETURNING history_id
        """),
        {"run_time": run_time},
    )

    new_count = len(new_result.fetchall())

    return new_count, updated_count


def main():
    with engine.begin() as conn:
        new_count, updated_count = sync_assignment_history(conn)

        total_history = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.crew_assignment_history
            """)
        ).scalar_one()

        closed_history = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.crew_assignment_history
                WHERE effective_to IS NOT NULL
            """)
        ).scalar_one()

        open_history = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.crew_assignment_history
                WHERE effective_to IS NULL
            """)
        ).scalar_one()

    print("Crew assignment history sync completed.")
    print(f"New assignments recorded: {new_count:,}")
    print(f"Status changes recorded: {updated_count:,}")
    print(f"Total history records: {total_history:,}")
    print(f"Closed history records: {closed_history:,}")
    print(f"Open history records: {open_history:,}")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
