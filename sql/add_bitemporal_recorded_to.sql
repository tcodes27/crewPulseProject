-- CrewPulse: Add system-time tracking to crew assignment history.
--
-- Purpose:
-- Add the ending boundary for database knowledge time.
--
-- Temporal model:
-- Business time: [effective_from, effective_to)
-- System time:   [recorded_at, recorded_to)
--
-- Existing records are preserved. Their recorded_to values remain NULL
-- because they have not been superseded by a historical correction.

BEGIN;

ALTER TABLE core.crew_assignment_history
ADD COLUMN recorded_to TIMESTAMPTZ;

ALTER TABLE core.crew_assignment_history
ADD CONSTRAINT valid_recorded_period
CHECK (
    recorded_to IS NULL
    OR recorded_to > recorded_at
);

COMMIT;
