"""
Data ingestion script.

Downloads the Zomato dataset from Hugging Face and preprocesses it
into a cleaned CSV for the recommendation engine.

Usage:
    python scripts/ingest.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path so we can import backend utilities
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from datasets import load_dataset

from backend.utils.preprocessing import preprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

# Paths
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_CSV = RAW_DIR / "zomato_raw.csv"
CLEANED_CSV = PROCESSED_DIR / "zomato_cleaned.csv"

# Dataset source
HF_DATASET = "ManikaSaini/zomato-restaurant-recommendation"


def download_dataset() -> pd.DataFrame:
    """Download the Zomato dataset from Hugging Face and return as DataFrame."""
    logger.info(f"Downloading dataset from Hugging Face: {HF_DATASET}")
    try:
        ds = load_dataset(HF_DATASET)
    except Exception as e:
        logger.error(f"Failed to download dataset: {e}")
        logger.error(
            "Check your network connection and ensure the dataset exists: "
            f"https://huggingface.co/datasets/{HF_DATASET}"
        )
        sys.exit(1)

    # Use the first available split (usually "train")
    split_name = list(ds.keys())[0]
    logger.info(f"Using split: '{split_name}' ({ds[split_name].num_rows} rows)")

    df = ds[split_name].to_pandas()
    return df


def save_raw(df: pd.DataFrame) -> None:
    """Save the raw dataset to disk for reference."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CSV, index=False)
    logger.info(f"Raw dataset saved to {RAW_CSV} ({len(df)} rows)")


def save_processed(df: pd.DataFrame) -> None:
    """Save the cleaned dataset to disk."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(CLEANED_CSV, index=False)
        logger.info(f"Cleaned dataset saved to {CLEANED_CSV} ({len(df)} rows)")
    except OSError as e:
        logger.error(f"Failed to save processed CSV: {e}")
        sys.exit(1)


def explore_dataset(df: pd.DataFrame) -> None:
    """Print summary statistics for validation."""
    print("\n" + "=" * 60)
    print("  DATASET SUMMARY")
    print("=" * 60)

    print(f"\n  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\n  Columns: {list(df.columns)}")

    print(f"\n  Data Types:")
    for col, dtype in df.dtypes.items():
        null_count = df[col].isnull().sum()
        null_pct = f" ({null_count / len(df) * 100:.1f}% null)" if null_count > 0 else ""
        print(f"    {col:30s} {str(dtype):10s}{null_pct}")

    if "location" in df.columns:
        unique_locations = df["location"].nunique()
        print(f"\n  Unique locations: {unique_locations}")
        top_locations = df["location"].value_counts().head(10)
        print("  Top 10 locations:")
        for loc, count in top_locations.items():
            print(f"    {loc:30s} {count:>5d} restaurants")

    if "cuisines" in df.columns:
        unique_cuisines = set()
        for c in df["cuisines"].dropna():
            for cuisine in str(c).split(","):
                cuisine = cuisine.strip()
                if cuisine and cuisine.lower() != "unknown":
                    unique_cuisines.add(cuisine)
        print(f"\n  Unique cuisines: {len(unique_cuisines)}")

    if "aggregate_rating" in df.columns:
        print(f"\n  Rating stats:")
        print(f"    Min:    {df['aggregate_rating'].min():.1f}")
        print(f"    Max:    {df['aggregate_rating'].max():.1f}")
        print(f"    Mean:   {df['aggregate_rating'].mean():.2f}")
        print(f"    Median: {df['aggregate_rating'].median():.1f}")

    if "average_cost_for_two" in df.columns:
        print(f"\n  Cost stats (Rs for two):")
        print(f"    Min:    Rs {df['average_cost_for_two'].min():.0f}")
        print(f"    Max:    Rs {df['average_cost_for_two'].max():.0f}")
        print(f"    Mean:   Rs {df['average_cost_for_two'].mean():.0f}")
        print(f"    Median: Rs {df['average_cost_for_two'].median():.0f}")

    print("\n" + "=" * 60)


def main():
    """Run the full ingestion pipeline."""
    print("\n--- Zomato Dataset Ingestion ---\n")

    # Step 1: Download
    raw_df = download_dataset()

    # Step 2: Save raw copy
    save_raw(raw_df)

    # Step 3: Preprocess
    logger.info("Running preprocessing pipeline...")
    cleaned_df = preprocess(raw_df)

    # Step 4: Save cleaned
    save_processed(cleaned_df)

    # Step 5: Explore & validate
    explore_dataset(cleaned_df)

    print("\n[OK] Ingestion complete! Cleaned data is ready at:")
    print(f"   {CLEANED_CSV}\n")


if __name__ == "__main__":
    main()
