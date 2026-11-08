import pytest

from src import ingest_airports


def test_missing_database_url_raises_clear_error(monkeypatch):
    """The pipeline should explain when DATABASE_URL is missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(
        RuntimeError,
        match="DATABASE_URL is missing from .env",
    ):
        ingest_airports.main()


def test_download_airports_propagates_source_error(monkeypatch):
    """A failed source request should propagate from pandas."""

    def fake_read_csv(*args, **kwargs):
        raise ConnectionError("Simulated airport source failure")

    monkeypatch.setattr(ingest_airports.pd, "read_csv", fake_read_csv)

    with pytest.raises(
        ConnectionError,
        match="Simulated airport source failure",
    ):
        ingest_airports.download_airports()


def test_download_failure_records_failed_pipeline_run(monkeypatch):
    """A source failure should mark the pipeline run as FAILED."""
    from contextlib import contextmanager

    executed = []
    disposed = []

    class FakeResult:
        def scalar_one(self):
            return 42

    class FakeConnection:
        def execute(self, statement, params=None):
            executed.append((str(statement), params or {}))
            if "INSERT INTO ops.pipeline_runs" in str(statement):
                return FakeResult()
            return None

    class FakeEngine:
        @contextmanager
        def begin(self):
            yield FakeConnection()

        def dispose(self):
            disposed.append(True)

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setattr(ingest_airports, "create_engine", lambda _: FakeEngine())

    def fake_download():
        raise ConnectionError("Simulated airport source failure")

    monkeypatch.setattr(ingest_airports, "download_airports", fake_download)

    with pytest.raises(ConnectionError, match="Simulated airport source failure"):
        ingest_airports.main()

    failed_updates = [
        params
        for statement, params in executed
        if "UPDATE ops.pipeline_runs" in statement
        and "'FAILED'" in statement
    ]

    assert len(failed_updates) == 1
    assert failed_updates[0]["run_id"] == 42
    assert failed_updates[0]["error"] == "Simulated airport source failure"
    assert disposed == [True]


def test_download_airports_reads_local_source(monkeypatch, tmp_path):
    """Local mode should read the cached CSV without a network request."""
    import pandas as pd

    source_file = tmp_path / "airports.csv"
    expected = pd.DataFrame({
        "id": [1],
        "ident": ["TEST"],
        "name": ["Test Airport"],
    })
    expected.to_csv(source_file, index=False)

    monkeypatch.setenv("AIRPORTS_SOURCE", "local")
    monkeypatch.setattr(ingest_airports, "RAW_FILE", source_file)

    result = ingest_airports.download_airports()

    pd.testing.assert_frame_equal(result, expected)


def test_download_airports_rejects_invalid_source(monkeypatch):
    """Unsupported source settings should fail clearly."""
    monkeypatch.setenv("AIRPORTS_SOURCE", "unknown")

    with pytest.raises(
        ValueError,
        match="AIRPORTS_SOURCE must be either 'remote' or 'local'",
    ):
        ingest_airports.download_airports()
