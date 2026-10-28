-- CrewPulse: Reusable Analytics Views
-- Note: Flight and crew data in this project are synthetic.

CREATE OR REPLACE VIEW analytics.vw_flight_performance_by_origin AS
SELECT
    origin_airport,
    COUNT(*) AS total_flights,
    COUNT(*) FILTER (
        WHERE flight_status = 'DELAYED'
    ) AS delayed_flights,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE flight_status = 'DELAYED'
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS delayed_flight_pct
FROM core.flights
GROUP BY origin_airport;

CREATE OR REPLACE VIEW analytics.vw_crew_coverage_by_flight AS
SELECT
    f.flight_id,
    f.flight_number,
    f.origin_airport,
    f.destination_airport,
    COUNT(ca.assignment_id) AS crew_assignment_count,
    CASE
        WHEN COUNT(ca.assignment_id) < 2
            THEN 'INSUFFICIENT'
        ELSE 'ADEQUATE'
    END AS crew_coverage_status
FROM core.flights f
LEFT JOIN core.crew_assignments ca
    ON f.flight_id = ca.flight_id
GROUP BY
    f.flight_id,
    f.flight_number,
    f.origin_airport,
    f.destination_airport;

CREATE OR REPLACE VIEW analytics.vw_route_activity AS
SELECT
    origin_airport,
    destination_airport,
    COUNT(*) AS total_flights,
    COUNT(*) FILTER (
        WHERE flight_status = 'DELAYED'
    ) AS delayed_flights
FROM core.flights
GROUP BY
    origin_airport,
    destination_airport;
