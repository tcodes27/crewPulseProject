
import pandas as pd
import pytest

from src.airport_transforms import prepare_airport_records


def sample_airports():
    """Create a small dataset with valid and invalid records."""
    return pd.DataFrame([
        {
            "iata_code": "ATL",
            "name": "Hartsfield-Jackson Atlanta International",
            "municipality": "Atlanta",
            "iso_country": "US",
        },
        {
            "iata_code": "LAX",
            "name": "Los Angeles International",
            "municipality": "Los Angeles",
            "iso_country": "US",
        },
        {
            "iata_code": None,
            "name": "Airport Without IATA",
            "municipality": "Unknown",
            "iso_country": "US",
        },
        {
            "iata_code": "ATL",
            "name": "Duplicate Atlanta Record",
            "municipality": "Atlanta",
            "iso_country": "US",
        },
        {
            "iata_code": "BOS",
            "name": "   ",
            "municipality": "Boston",
            "iso_country": "US",
        },
    ])


def test_airport_metrics_count_excluded_records():
    cleaned, metrics = prepare_airport_records(sample_airports())

    assert metrics["records_read"] == 5
    assert metrics["invalid_iata_count"] == 1
    assert metrics["duplicate_count"] == 1
    assert metrics["missing_required_count"] == 1
    assert metrics["records_rejected"] == 3
    assert metrics["records_loaded"] == 2


def test_only_unique_valid_airports_are_returned():
    cleaned, _ = prepare_airport_records(sample_airports())

    assert cleaned["airport_code"].tolist() == ["ATL", "LAX"]
    assert cleaned["airport_name"].str.strip().ne("").all()


def test_missing_source_column_raises_clear_error():
    airports = sample_airports().drop(columns=["iso_country"])

    with pytest.raises(ValueError, match="iso_country"):
        prepare_airport_records(airports)
