from datetime import datetime, timezone

from sqlalchemy import text


def correct_assignment_history(
    conn,
    history_id: int,
    corrected_status: str,
    correction_reason: str,
):
    """
    Supersede the current system-time version of a history record.

    The original effective-time period is preserved.
    The caller is responsible for transaction management.
    """
    if not corrected_status or not corrected_status.strip():
        raise ValueError("Corrected status is required.")

    if not correction_reason or not correction_reason.strip():
        raise ValueError("Correction reason is required.")

    run_time = datetime.now(timezone.utc)

    original = conn.execute(
        text("""
            SELECT
                history_id,
                assignment_id,
                crew_id,
                flight_id,
                assignment_status,
                effective_from,
                effective_to
            FROM core.crew_assignment_history
            WHERE history_id = :history_id
              AND recorded_to IS NULL
            FOR UPDATE
        """),
        {"history_id": history_id},
    ).mappings().one_or_none()

    if original is None:
        raise ValueError(
            f"No current system-time history record found for ID {history_id}."
        )

    conn.execute(
        text("""
            UPDATE core.crew_assignment_history
            SET recorded_to = :run_time
            WHERE history_id = :history_id
              AND recorded_to IS NULL
        """),
        {
            "run_time": run_time,
            "history_id": history_id,
        },
    )

    result = conn.execute(
        text("""
            INSERT INTO core.crew_assignment_history (
                assignment_id,
                crew_id,
                flight_id,
                assignment_status,
                effective_from,
                effective_to,
                recorded_at,
                change_reason
            )
            VALUES (
                :assignment_id,
                :crew_id,
                :flight_id,
                :assignment_status,
                :effective_from,
                :effective_to,
                :recorded_at,
                :change_reason
            )
            RETURNING history_id
        """),
        {
            "assignment_id": original["assignment_id"],
            "crew_id": original["crew_id"],
            "flight_id": original["flight_id"],
            "assignment_status": corrected_status,
            "effective_from": original["effective_from"],
            "effective_to": original["effective_to"],
            "recorded_at": run_time,
            "change_reason": correction_reason,
        },
    )

    return result.scalar_one()
