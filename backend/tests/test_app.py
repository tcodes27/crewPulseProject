from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from backend.app import get_flights


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def one(self):
        return self.rows[0]


def make_session(flight_rows, kpis):
    session = MagicMock()
    session.begin.return_value.__enter__.return_value = None
    session.execute.side_effect = [None, FakeResult(flight_rows), FakeResult([kpis])]
    return session


def test_get_flights_returns_rows_and_kpis_and_enforces_read_only():
    departure = datetime(2026, 11, 10, 14, 30, tzinfo=timezone.utc)
    row = {
        "flight_id": 7,
        "flight_number": "CP0007",
        "origin": "JFK",
        "destination": "ATL",
        "scheduled_departure": departure,
        "status": "SCHEDULED",
        "crew_assignments": 2,
        "crew_coverage": "ADEQUATE",
    }
    kpis = {
        "total_flights": 1,
        "scheduled_flights": 1,
        "delayed_flights": 0,
        "crew_assignments": 2,
    }
    session = make_session([row], kpis)

    result = get_flights(session)

    assert result == {"flights": [row], "kpis": kpis}
    assert "SET TRANSACTION READ ONLY" in str(session.execute.call_args_list[0].args[0])


def test_get_flights_returns_zero_kpis_when_database_is_empty():
    kpis = {
        "total_flights": 0,
        "scheduled_flights": 0,
        "delayed_flights": 0,
        "crew_assignments": 0,
    }

    result = get_flights(make_session([], kpis))

    assert result == {"flights": [], "kpis": kpis}


def test_get_flights_hides_database_errors():
    session = MagicMock()
    session.begin.return_value.__enter__.return_value = None
    session.execute.side_effect = OperationalError("SELECT", {}, Exception("private detail"))

    try:
        get_flights(session)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Flight data is temporarily unavailable."
        assert "private detail" not in str(exc.detail)
    else:
        raise AssertionError("Expected a sanitized service-unavailable response")
