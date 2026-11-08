import os
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(title="CrewPulse Operations API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Build the database connection lazily from the root .env file."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in the project environment.")

    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    try:
        factory = get_session_factory()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Database is not configured.") from exc

    with factory() as session:
        yield session


FLIGHTS_QUERY = text(
    """
    SELECT
        f.flight_id,
        f.flight_number,
        f.origin_airport AS origin,
        f.destination_airport AS destination,
        f.scheduled_departure,
        f.flight_status AS status,
        COUNT(ca.assignment_id)::INTEGER AS crew_assignments,
        CASE
            WHEN COUNT(ca.assignment_id) < 2 THEN 'INSUFFICIENT'
            ELSE 'ADEQUATE'
        END AS crew_coverage
    FROM core.flights AS f
    LEFT JOIN core.crew_assignments AS ca
        ON ca.flight_id = f.flight_id
    GROUP BY f.flight_id
    ORDER BY f.scheduled_departure, f.flight_number
    """
)

FLIGHT_KPIS_QUERY = text(
    """
    SELECT
        COUNT(*)::INTEGER AS total_flights,
        COUNT(*) FILTER (WHERE flight_status = 'SCHEDULED')::INTEGER
            AS scheduled_flights,
        COUNT(*) FILTER (WHERE flight_status = 'DELAYED')::INTEGER
            AS delayed_flights,
        (
            SELECT COUNT(*)::INTEGER
            FROM core.crew_assignments
        ) AS crew_assignments
    FROM core.flights
    """
)


@app.get("/api/flights")
def get_flights(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Return flight rows and overview counts using a read-only transaction."""
    try:
        with session.begin():
            # Enforce read-only access for this transaction, even if the
            # configured database role has broader permissions.
            session.execute(text("SET TRANSACTION READ ONLY"))
            flight_rows = session.execute(FLIGHTS_QUERY).mappings().all()
            kpis = session.execute(FLIGHT_KPIS_QUERY).mappings().one()

        return {
            "flights": [dict(row) for row in flight_rows],
            "kpis": dict(kpis),
        }
    except SQLAlchemyError as exc:
        # Keep database details and connection configuration out of responses.
        raise HTTPException(
            status_code=503,
            detail="Flight data is temporarily unavailable.",
        ) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
