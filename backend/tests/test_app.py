from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from backend.app import (
    get_flights,
    get_pipeline_data_quality,
    get_pipeline_runs,
    get_pipeline_summary,
)


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


def make_readonly_session(result):
    session = MagicMock()
    session.begin.return_value.__enter__.return_value = None
    session.execute.side_effect = [None, result]
    return session


def test_pipeline_summary_returns_counts_and_enforces_read_only():
    summary = {
        "total_runs": 3, "successful_runs": 1, "failed_runs": 1,
        "other_runs": 1, "total_data_quality_checks": 4,
        "pass_checks": 2, "warning_checks": 1, "fail_checks": 1,
        "latest_execution_at": datetime(2026, 11, 10, tzinfo=timezone.utc),
    }
    session = make_readonly_session(FakeResult([summary]))

    assert get_pipeline_summary(session) == summary
    assert "SET TRANSACTION READ ONLY" in str(session.execute.call_args_list[0].args[0])


def test_pipeline_summary_returns_zero_counts_when_empty():
    summary = {
        "total_runs": 0, "successful_runs": 0, "failed_runs": 0,
        "other_runs": 0, "total_data_quality_checks": 0,
        "pass_checks": 0, "warning_checks": 0, "fail_checks": 0,
        "latest_execution_at": None,
    }
    assert get_pipeline_summary(make_readonly_session(FakeResult([summary]))) == summary


def test_pipeline_runs_returns_history_with_bounded_limit_and_read_only():
    row = {"run_id": 8, "pipeline_name": "crew_pulse", "status": "SUCCESS"}
    session = make_readonly_session(FakeResult([row]))

    assert get_pipeline_runs(limit=12, session=session) == {"runs": [row]}
    assert "SET TRANSACTION READ ONLY" in str(session.execute.call_args_list[0].args[0])
    statement, parameters = session.execute.call_args_list[1].args
    assert "ORDER BY started_at DESC" in str(statement)
    assert parameters == {"limit": 12}


def test_pipeline_runs_returns_empty_history():
    assert get_pipeline_runs(session=make_readonly_session(FakeResult([]))) == {"runs": []}


def test_data_quality_filters_by_run_and_limit_and_enforces_read_only():
    row = {"result_id": 4, "run_id": 9, "table_name": "core.airports", "status": "PASS"}
    session = make_readonly_session(FakeResult([row]))

    assert get_pipeline_data_quality(run_id=9, limit=5, session=session) == {"results": [row]}
    assert "SET TRANSACTION READ ONLY" in str(session.execute.call_args_list[0].args[0])
    statement, parameters = session.execute.call_args_list[1].args
    assert "ORDER BY checked_at DESC" in str(statement)
    assert ":run_id" in str(statement)
    assert parameters == {"run_id": 9, "limit": 5}


def test_data_quality_returns_empty_history():
    assert get_pipeline_data_quality(session=make_readonly_session(FakeResult([]))) == {"results": []}


def test_pipeline_endpoints_hide_database_errors():
    endpoints = [
        (get_pipeline_summary, {}),
        (get_pipeline_runs, {}),
        (get_pipeline_data_quality, {}),
    ]
    for endpoint, kwargs in endpoints:
        session = MagicMock()
        session.begin.return_value.__enter__.return_value = None
        session.execute.side_effect = OperationalError("SELECT", {}, Exception("private detail"))
        try:
            endpoint(session=session, **kwargs)
        except HTTPException as exc:
            assert exc.status_code == 503
            assert exc.detail == "Pipeline monitoring data is temporarily unavailable."
            assert "private detail" not in str(exc.detail)
        else:
            raise AssertionError("Expected a sanitized service-unavailable response")
