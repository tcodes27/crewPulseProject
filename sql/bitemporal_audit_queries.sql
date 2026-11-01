-- 1. BITEMPORAL OVERLAP AUDIT
-- A conflict exists only when BOTH time dimensions overlap.
-- Adjacent periods are valid.

SELECT
    h1.assignment_id,
    h1.history_id AS first_history_id,
    h2.history_id AS second_history_id,
    h1.effective_from AS first_effective_start,
    h1.effective_to AS first_effective_end,
    h2.effective_from AS second_effective_start,
    h2.effective_to AS second_effective_end,
    h1.recorded_at AS first_recorded_start,
    h1.recorded_to AS first_recorded_end,
    h2.recorded_at AS second_recorded_start,
    h2.recorded_to AS second_recorded_end
FROM core.crew_assignment_history AS h1
JOIN core.crew_assignment_history AS h2
    ON h1.assignment_id = h2.assignment_id
   AND h1.history_id < h2.history_id
WHERE
    h1.effective_from < COALESCE(h2.effective_to, 'infinity'::timestamptz)
    AND h2.effective_from < COALESCE(h1.effective_to, 'infinity'::timestamptz)
    AND h1.recorded_at < COALESCE(h2.recorded_to, 'infinity'::timestamptz)
    AND h2.recorded_at < COALESCE(h1.recorded_to, 'infinity'::timestamptz)
ORDER BY h1.assignment_id;
