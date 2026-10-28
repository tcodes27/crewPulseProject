-- CrewPulse: Crew Operations Analytics
-- Purpose: Analyze flights, crew assignments, and assignment history.
-- Note: This project uses synthetic crew operations data.

-- 1. Count flights by origin airport
SELECT
    origin_airport,
    COUNT(*) AS total_flights
FROM core.flights
GROUP BY origin_airport
ORDER BY total_flights DESC;


-- 2. Count crew assignments per flight
SELECT
    f.flight_id,
    f.flight_number,
    COUNT(ca.assignment_id) AS crew_assignment_count
FROM core.flights f
LEFT JOIN core.crew_assignments ca
    ON f.flight_id = ca.flight_id
GROUP BY f.flight_id, f.flight_number
ORDER BY f.flight_number;


-- 3. Find flights with fewer than two crew assignments
SELECT
    f.flight_id,
    f.flight_number,
    COUNT(ca.assignment_id) AS crew_assignment_count
FROM core.flights f
LEFT JOIN core.crew_assignments ca
    ON f.flight_id = ca.flight_id
GROUP BY f.flight_id, f.flight_number
HAVING COUNT(ca.assignment_id) < 2
ORDER BY f.flight_number;


-- 4. Review assignment assignment_status, history
SELECT
    assignment_id,
    assignment_status,
    effective_from,
    effective_to,
    change_reason
FROM core.crew_assignment_history
ORDER BY assignment_id, effective_from;
