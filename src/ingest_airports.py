
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load database settings from .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from the .env file.")

# Public airport reference data from OurAirports
AIRPORTS_URL = "https://ourairports.com/data/airports.csv"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "airports.csv"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading airport reference data...")
    airports = pd.read_csv(AIRPORTS_URL, low_memory=False)
    airports.to_csv(RAW_FILE, index=False)
    print(f"Downloaded {len(airports):,} airport records.")

    # Keep airports with a three-letter IATA code.
    airports = airports[
        airports["iata_code"].notna()
        & airports["iata_code"].str.fullmatch(r"[A-Z]{3}", na=False)
    ].copy()

    # Map the source columns to our database schema.
    airports = airports[
        ["iata_code", "name", "municipality", "iso_country"]
    ].rename(
        columns={
            "iata_code": "airport_code",
            "name": "airport_name",
            "municipality": "city",
            "iso_country": "country",
        }
    )

    airports = airports.drop_duplicates(subset=["airport_code"])
    airports = airports.where(pd.notna(airports), None)

    print(f"Loading {len(airports):,} airports into PostgreSQL...")

    engine = create_engine(DATABASE_URL)

    try:
        with engine.begin() as connection:
            # Upsert lets us rerun the pipeline without duplicate airport codes.
            connection.execute(
                text("""
                    INSERT INTO core.airports
                        (airport_code, airport_name, city, country)
                    VALUES
                        (:airport_code, :airport_name, :city, :country)
                    ON CONFLICT (airport_code) DO UPDATE SET
                        airport_name = EXCLUDED.airport_name,
                        city = EXCLUDED.city,
                        country = EXCLUDED.country
                """),
                airports.to_dict(orient="records"),
            )

        print("Airport data loaded successfully.")

    finally:
        engine.dispose()

    print(f"Raw source file saved to: {RAW_FILE}")


if __name__ == "__main__":
    main()
