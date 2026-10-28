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
