CREATE SCHEMA core;

CREATE TABLE core.airports (
    airport_code VARCHAR(3) PRIMARY KEY,
    airport_name TEXT NOT NULL,
    city TEXT,
    country TEXT
);

CREATE TABLE core.crew_members (
    crew_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crew_code VARCHAR(20) NOT NULL UNIQUE,
    crew_role TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE core.flights (
    flight_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flight_number VARCHAR(10) NOT NULL,
    origin_airport VARCHAR(3) NOT NULL
        REFERENCES core.airports(airport_code),
    destination_airport VARCHAR(3) NOT NULL
        REFERENCES core.airports(airport_code),
    scheduled_departure TIMESTAMPTZ NOT NULL,
    scheduled_arrival TIMESTAMPTZ NOT NULL,
    flight_status TEXT NOT NULL DEFAULT 'SCHEDULED',
    CONSTRAINT valid_route
        CHECK (origin_airport <> destination_airport),
    CONSTRAINT valid_times
        CHECK (scheduled_arrival > scheduled_departure)
);

CREATE TABLE core.crew_assignments (
    assignment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flight_id BIGINT NOT NULL REFERENCES core.flights(flight_id),
    crew_id BIGINT NOT NULL REFERENCES core.crew_members(crew_id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assignment_status TEXT NOT NULL DEFAULT 'ASSIGNED'
);

CREATE TABLE core.crew_assignment_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assignment_id BIGINT NOT NULL
        REFERENCES core.crew_assignments(assignment_id),
    crew_id BIGINT NOT NULL REFERENCES core.crew_members(crew_id),
    flight_id BIGINT NOT NULL REFERENCES core.flights(flight_id),
    assignment_status TEXT NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT,
    CONSTRAINT valid_effective_period
        CHECK (effective_to IS NULL OR effective_to > effective_from)
);
-- Sample airports
INSERT INTO core.airports
    (airport_code, airport_name, city, country)
VALUES
    ('ATL', 'Hartsfield-Jackson Atlanta International', 'Atlanta', 'USA'),
    ('LAX', 'Los Angeles International', 'Los Angeles', 'USA');

-- Sample crew members
INSERT INTO core.crew_members (crew_code, crew_role)
VALUES
    ('TEST-PILOT-01', 'PILOT'),
    ('TEST-CABIN-01', 'CABIN');

-- Sample flight
INSERT INTO core.flights
    (flight_number, origin_airport, destination_airport,
     scheduled_departure, scheduled_arrival)
VALUES
    ('CP100', 'ATL', 'LAX',
     '2026-11-01 09:00:00+00', '2026-11-01 12:00:00+00');

-- Two crew assignments for the flight
INSERT INTO core.crew_assignments
    (flight_id, crew_id, assignment_status)
VALUES
    (1, 1, 'ASSIGNED'),
    (1, 2, 'ASSIGNED');

-- One current history record per assignment
INSERT INTO core.crew_assignment_history
    (assignment_id, crew_id, flight_id, assignment_status,
     effective_from, change_reason)
VALUES
    (1, 1, 1, 'ASSIGNED', CURRENT_TIMESTAMP, 'Test setup'),
    (2, 2, 1, 'ASSIGNED', CURRENT_TIMESTAMP, 'Test setup');
