-- CrewPulse: Delay Analysis by Departure Hour
-- Purpose: Compare flight delay rates across departure hours.
-- Data: Synthetic flight operations data.
-- Rule: Only include hours with at least 8 flights.

SELECT
    EXTRACT(HOUR FROM scheduled_departure) AS departure_hour,
    COUNT(*) AS total_flights,
    COUNT(*) FILTER (
        WHERE flight_status = 'DELAYED'
    ) AS delayed_flights,
    ROUND(
        COUNT(*) FILTER (
            WHERE flight_status = 'DELAYED'
        ) * 100.0 / COUNT(*),
        2
    ) AS delayed_flight_pct
FROM core.flights
GROUP BY departure_hour
HAVING COUNT(*) >= 8
ORDER BY delayed_flight_pct DESC;
