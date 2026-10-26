import os
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing. Check your .env file.")

engine = create_engine(DATABASE_URL)

RANDOM_SEED = 42
CREW_COUNT = 100
FLIGHT_COUNT = 200

random.seed(RANDOM_SEED)

CREW_ROLES = ["PILOT", "COPILOT", "FLIGHT_ATTENDANT"]
FLIGHT_STATUSES = ["SCHEDULED", "SCHEDULED", "SCHEDULED", "DELAYED"]
ASSIGNMENT_STATUSES = ["ASSIGNED", "ASSIGNED", "ASSIGNED", "CONFIRMED"]


def generate_crew(conn):
    """Insert fictional crew members without duplicating crew codes."""
    for number in range(1, CREW_COUNT + 1):
        conn.execute(
            text("""
                INSERT INTO core.crew_members (
                    crew_code, crew_role, active
                )
                VALUES (:crew_code, :crew_role, TRUE)
                ON CONFLICT (crew_code) DO NOTHING
            """),
            {
                "crew_code": f"SIM{number:04d}",
                "crew_role": random.choice(CREW_ROLES),
            },
        )

    rows = conn.execute(
        text("""
            SELECT crew_id, crew_code, crew_role
            FROM core.crew_members
            WHERE crew_code LIKE 'SIM%'
            ORDER BY crew_code
        """)
    ).mappings().all()

    return [dict(row) for row in rows]


def generate_flights(conn, airports):
    """Create fictional flights, skipping existing synthetic flight numbers."""
    flights = []
    start_time = datetime.now(timezone.utc) + timedelta(days=1)

    for number in range(1, FLIGHT_COUNT + 1):
        flight_number = f"CP{number:04d}"

        existing_flight = conn.execute(
            text("""
                SELECT flight_id
                FROM core.flights
                WHERE flight_number = :flight_number
            """),
            {"flight_number": flight_number},
        ).scalar_one_or_none()

        if existing_flight is not None:
            flights.append(
                {
                    "flight_id": existing_flight,
                    "flight_number": flight_number,
                }
            )
            continue

        origin, destination = random.sample(airports, 2)
        departure = start_time + timedelta(
            minutes=random.randint(0, 7 * 24 * 60)
        )
        arrival = departure + timedelta(
            minutes=random.randint(45, 360)
        )

        result = conn.execute(
            text("""
                INSERT INTO core.flights (
                    flight_number,
                    origin_airport,
                    destination_airport,
                    scheduled_departure,
                    scheduled_arrival,
                    flight_status
                )
                VALUES (
                    :flight_number,
                    :origin,
                    :destination,
                    :departure,
                    :arrival,
                    :status
                )
                RETURNING flight_id
            """),
            {
                "flight_number": flight_number,
                "origin": origin,
                "destination": destination,
                "departure": departure,
                "arrival": arrival,
                "status": random.choice(FLIGHT_STATUSES),
            },
        )

        flights.append(
            {
                "flight_id": result.scalar_one(),
                "flight_number": flight_number,
            }
        )

    return flights


def assign_crew(conn, flights, crew):
    """Assign two crew members per flight without duplicate pairs."""
    assignments_created = 0

    if len(crew) < 2:
        raise ValueError("At least two synthetic crew members are required.")

    for flight in flights:
        existing_count = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.crew_assignments
                WHERE flight_id = :flight_id
            """),
            {"flight_id": flight["flight_id"]},
        ).scalar_one()

        if existing_count > 0:
            continue

        for member in random.sample(crew, 2):
            conn.execute(
                text("""
                    INSERT INTO core.crew_assignments (
                        flight_id, crew_id, assignment_status
                    )
                    VALUES (
                        :flight_id, :crew_id, :assignment_status
                    )
                """),
                {
                    "flight_id": flight["flight_id"],
                    "crew_id": member["crew_id"],
                    "assignment_status": random.choice(
                        ASSIGNMENT_STATUSES
                    ),
                },
            )
            assignments_created += 1

    return assignments_created


def main():
    with engine.begin() as conn:
        airports = conn.execute(
            text("""
                SELECT airport_code
                FROM core.airports
                ORDER BY airport_code
            """)
        ).scalars().all()

        if len(airports) < 2:
            raise ValueError(
                "At least two airports are required. "
                "Run the airport ingestion pipeline first."
            )

        crew = generate_crew(conn)
        flights = generate_flights(conn, airports)
        assignments_created = assign_crew(conn, flights, crew)

        total_flights = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.flights
                WHERE flight_number LIKE 'CP%'
            """)
        ).scalar_one()

        total_assignments = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM core.crew_assignments ca
                JOIN core.flights f ON f.flight_id = ca.flight_id
                WHERE f.flight_number LIKE 'CP%'
            """)
        ).scalar_one()

    print("Synthetic operations data processed successfully.")
    print(f"Airport codes available: {len(airports):,}")
    print(f"Synthetic crew records available: {len(crew):,}")
    print(f"Synthetic flights available: {total_flights:,}")
    print(f"New crew assignments created: {assignments_created:,}")
    print(f"Total synthetic crew assignments: {total_assignments:,}")
    print("Database transaction committed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise
    finally:
        engine.dispose()
