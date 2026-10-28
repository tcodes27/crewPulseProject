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
