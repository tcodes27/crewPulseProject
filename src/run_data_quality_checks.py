
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

QUALITY_CHECKS = [
    {
        "table_name": "core.flights",
        "check_name": "invalid_flight_schedule",
        "description": "Flights whose arrival is not after departure.",
        "sql": """
            SELECT COUNT(*)
            FROM core.flights
            WHERE scheduled_arrival <= scheduled_departure
        """,
    },
    {
        "table_name": "core.flights",
        "check_name": "invalid_flight_route",
        "description": "Flights whose origin and destination are the same.",
        "sql": """
            SELECT COUNT(*)
            FROM core.flights
            WHERE origin_airport = destination_airport
        """,
    },
    {
        "table_name": "core.crew_assignments",
        "check_name": "duplicate_crew_assignments",
        "description": "Extra assignments for the same crew member and flight.",
        "sql": """
            SELECT COALESCE(SUM(assignment_count - 1), 0)
            FROM (
                SELECT COUNT(*) AS assignment_count
                FROM core.crew_assignments
                GROUP BY flight_id, crew_id
                HAVING COUNT(*) > 1
            ) duplicates
        """,
    },
    {
        "table_name": "core.crew_assignments",
        "check_name": "assignments_without_current_history",
        "description": "Assignments without exactly one current history record.",
        "sql": """
            SELECT COUNT(*)
            FROM core.crew_assignments a
            LEFT JOIN (
                SELECT assignment_id, COUNT(*) AS current_count
                FROM core.crew_assignment_history
                WHERE effective_to IS NULL
                GROUP BY assignment_id
            ) h ON h.assignment_id = a.assignment_id
            WHERE COALESCE(h.current_count, 0) <> 1
        """,
    },
    {
        "table_name": "core.crew_assignment_history",
        "check_name": "history_assignment_mismatch",
        "description": "History records whose crew or flight differs from the assignment.",
        "sql": """
            SELECT COUNT(*)
            FROM core.crew_assignment_history h
            JOIN core.crew_assignments a
              ON a.assignment_id = h.assignment_id
            WHERE h.crew_id <> a.crew_id
               OR h.flight_id <> a.flight_id
        """,
    },
]


def run_data_quality_checks():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing. Check your local .env file."
        )

    engine = create_engine(DATABASE_URL)
    run_id = None

    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    INSERT INTO ops.pipeline_runs (pipeline_name)
                    VALUES (:pipeline_name)
                    RETURNING run_id
                """),
                {"pipeline_name": "crew_pulse_data_quality"},
            )
            run_id = result.scalar_one()

        passed = 0
        failed = 0

        for check in QUALITY_CHECKS:
            try:
                with engine.connect() as connection:
                    failed_records = connection.execute(
                        text(check["sql"])
                    ).scalar_one()

                check_status = "PASS" if failed_records == 0 else "FAIL"
                details = (
                    f'{check["description"]} '
                    f"Detected {failed_records} failing record(s)."
                )

                with engine.begin() as connection:
                    connection.execute(
                        text("""
                            INSERT INTO ops.data_quality_results (
                                run_id,
                                table_name,
                                check_name,
                                failed_records,
                                check_status,
                                details
                            )
                            VALUES (
                                :run_id,
                                :table_name,
                                :check_name,
                                :failed_records,
                                :check_status,
                                :details
                            )
                        """),
                        {
                            "run_id": run_id,
                            "table_name": check["table_name"],
                            "check_name": check["check_name"],
                            "failed_records": failed_records,
                            "check_status": check_status,
                            "details": details,
                        },
                    )

                if check_status == "PASS":
                    passed += 1
                else:
                    failed += 1

                print(
                    f'{check["check_name"]}: {check_status} '
                    f"({failed_records} failing records)"
                )

            except Exception as error:
                failed += 1
                details = f"Check execution error: {error}"

                with engine.begin() as connection:
                    connection.execute(
                        text("""
                            INSERT INTO ops.data_quality_results (
                                run_id,
                                table_name,
                                check_name,
                                failed_records,
                                check_status,
                                details
                            )
                            VALUES (
                                :run_id,
                                :table_name,
                                :check_name,
                                :failed_records,
                                :check_status,
                                :details
                            )
                        """),
                        {
                            "run_id": run_id,
                            "table_name": check["table_name"],
                            "check_name": check["check_name"],
                            "failed_records": 0,
                            "check_status": "FAIL",
                            "details": details[:2000],
                        },
                    )

                print(f'{check["check_name"]}: ERROR — {error}')

        final_status = "SUCCESS" if failed == 0 else "FAILED"

        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE ops.pipeline_runs
                    SET finished_at = CURRENT_TIMESTAMP,
                        run_status = :run_status,
                        records_read = :records_read,
                        records_rejected = :records_rejected,
                        error_message = :error_message
                    WHERE run_id = :run_id
                """),
                {
                    "run_id": run_id,
                    "run_status": final_status,
                    "records_read": len(QUALITY_CHECKS),
                    "records_rejected": failed,
                    "error_message": (
                        f"{failed} check(s) failed."
                        if failed else None
                    ),
                },
            )

        print(
            f"\nPipeline run {run_id}: {final_status}. "
            f"{passed} passed; {failed} failed."
        )

    except Exception as error:
        if run_id is not None:
            with engine.begin() as connection:
                connection.execute(
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
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    run_data_quality_checks()
