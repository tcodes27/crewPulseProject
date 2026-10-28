
import pandas as pd


REQUIRED_SOURCE_COLUMNS = [
    "iata_code",
    "name",
    "municipality",
    "iso_country",
]


def prepare_airport_records(airports: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean airport records and return counts for pipeline monitoring."""

    records_read = len(airports)

    missing_columns = [
        column
        for column in REQUIRED_SOURCE_COLUMNS
        if column not in airports.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Source data is missing columns: {missing_columns}"
        )

    # Keep only valid three-letter IATA codes.
    valid_code = airports["iata_code"].str.fullmatch(
        r"[A-Z]{3}", na=False
    )
    selected = airports[valid_code].copy()
    invalid_iata_count = records_read - len(selected)

    # Count and remove duplicate codes.
    duplicate_count = int(selected["iata_code"].duplicated().sum())
    selected = selected.drop_duplicates(subset=["iata_code"])

    # Rename source columns to match the database.
    selected = selected[REQUIRED_SOURCE_COLUMNS].rename(
        columns={
            "iata_code": "airport_code",
            "name": "airport_name",
            "municipality": "city",
            "iso_country": "country",
        }
    )

    # Remove records missing a required code or airport name.
    missing_required = (
        selected["airport_code"].isna()
        | selected["airport_name"].isna()
        | selected["airport_name"].astype(str).str.strip().eq("")
    )
    missing_required_count = int(missing_required.sum())
    selected = selected[~missing_required].copy()

    records_rejected = (
        invalid_iata_count
        + duplicate_count
        + missing_required_count
    )

    # Convert pandas missing values to None for database insertion.
    selected = selected.astype(object).where(
        pd.notna(selected), None
    )

    metrics = {
        "records_read": records_read,
        "invalid_iata_count": invalid_iata_count,
        "duplicate_count": duplicate_count,
        "missing_required_count": missing_required_count,
        "records_rejected": records_rejected,
        "records_loaded": len(selected),
    }

    return selected, metrics
