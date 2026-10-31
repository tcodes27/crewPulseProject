-- ============================================================
-- CrewPulse: Temporal Crew Assignment Queries
-- Purpose: Explore effective-time and recorded-time history.
-- Data: Synthetic portfolio data; not actual airline operations.
-- ============================================================


-- 1. EFFECTIVE-TIME AS-OF QUERY
-- Question: What assignment status was effective at this time?
-- Change the timestamp to investigate another point in time.

WITH parameters AS (
    SELECT TIMESTAMPTZ '2026-10-26 18:50:00-04' AS effective_at
)
SELECT
    h.assignment_id,
    h.crew_id,
    h.flight_id,
    h.assignment_status,
    h.effective_from,
    h.effective_to,
    h.recorded_at
FROM core.crew_assignment_history AS h
CROSS JOIN parameters AS p
WHERE h.effective_from <= p.effective_at
  AND (
      h.effective_to IS NULL
      OR p.effective_at < h.effective_to
  )
ORDER BY h.assignment_id;


-- 2. TWO-DIMENSIONAL AS-OF QUERY
-- Question: What did the database know at a given time
-- about the status that was effective at another time?
--
-- effective_at = business-valid time
-- known_at     = database-recorded time
--
-- Limitation: This filters on recorded_at, but without a
-- recorded_to column it cannot reconstruct every later
-- correction to the database's historical knowledge.

WITH parameters AS (
    SELECT
        TIMESTAMPTZ '2026-10-26 18:50:00-04' AS effective_at,
        TIMESTAMPTZ '2026-10-26 18:50:00-04' AS known_at
)
SELECT
    h.assignment_id,
    h.crew_id,
    h.flight_id,
    h.assignment_status,
    h.effective_from,
    h.effective_to,
    h.recorded_at
FROM core.crew_assignment_history AS h
CROSS JOIN parameters AS p
WHERE h.effective_from <= p.effective_at
  AND (
      h.effective_to IS NULL
      OR p.effective_at < h.effective_to
  )
  AND h.recorded_at <= p.known_at
ORDER BY h.assignment_id;


-- 3. ASSIGNMENT STATUS TIMELINE
-- Question: How has one assignment changed over time?
-- Change assignment_id to inspect another assignment.

SELECT
    assignment_id,
    assignment_status,
    effective_from,
    effective_to,
    recorded_at,
    change_reason
FROM core.crew_assignment_history
WHERE assignment_id = 1
ORDER BY effective_from, recorded_at;


-- 4. ASSIGNMENTS WITH MULTIPLE HISTORY VERSIONS
-- Question: Which assignments have more than one history row?

SELECT
    assignment_id,
    COUNT(*) AS history_version_count,
    MIN(effective_from) AS first_effective_time,
    MAX(effective_from) AS latest_effective_time
FROM core.crew_assignment_history
GROUP BY assignment_id
HAVING COUNT(*) > 1
ORDER BY history_version_count DESC, assignment_id;


-- 5. EFFECTIVE-TIME OVERLAP CHECK
-- Question: Do two history periods for the same assignment overlap?
-- Adjacent periods are valid; an end equal to the next start
-- is not considered an overlap.

SELECT
    h1.assignment_id,
    h1.history_id AS first_history_id,
    h2.history_id AS second_history_id,
    h1.effective_from AS first_start,
    h1.effective_to AS first_end,
    h2.effective_from AS second_start,
    h2.effective_to AS second_end
FROM core.crew_assignment_history AS h1
JOIN core.crew_assignment_history AS h2
    ON h1.assignment_id = h2.assignment_id
   AND h1.history_id < h2.history_id
WHERE h1.effective_from < COALESCE(h2.effective_to, 'infinity'::timestamptz)
  AND h2.effective_from < COALESCE(h1.effective_to, 'infinity'::timestamptz)
ORDER BY h1.assignment_id;


-- 6. HISTORY RECORD SUMMARY
-- Question: How much history is currently stored?

SELECT
    COUNT(*) AS total_history_records,
    COUNT(DISTINCT assignment_id) AS unique_assignments,
    COUNT(*) FILTER (WHERE effective_to IS NULL) AS open_effective_periods,
    COUNT(*) FILTER (WHERE effective_to IS NOT NULL) AS closed_effective_periods,
    COUNT(DISTINCT assignment_id)
        FILTER (
            WHERE assignment_id IN (
                SELECT assignment_id
                FROM core.crew_assignment_history
                GROUP BY assignment_id
                HAVING COUNT(*) > 1
            )
        ) AS assignments_with_multiple_versions
FROM core.crew_assignment_history;
