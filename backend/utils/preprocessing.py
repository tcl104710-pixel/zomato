"""
Data preprocessing utilities.

Provides reusable functions for cleaning and normalizing
the raw Zomato dataset.
"""

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

# Maps raw column names (after snake_case normalization) to our standard names.
# Only columns we actually need are listed here.
COLUMN_RENAME_MAP = {
    "name": "restaurant_name",
    "rate": "aggregate_rating",
    "approx_costfor_two_people": "average_cost_for_two",
    "rest_type": "restaurant_type",
    "listed_incity": "city",
    # These stay as-is: location, cuisines, votes, online_order, book_table
}

# Columns to keep in the final cleaned output
KEEP_COLUMNS = [
    "restaurant_name",
    "location",
    "city",
    "cuisines",
    "average_cost_for_two",
    "aggregate_rating",
    "votes",
    "restaurant_type",
    "online_order",
    "book_table",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and snake_case all column names, then rename to standard names."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "_", regex=True)
    )
    logger.info(f"Raw columns: {list(df.columns)}")

    # Rename to our standard names
    df = df.rename(columns=COLUMN_RENAME_MAP)
    logger.info(f"Renamed columns: {list(df.columns)}")

    return df


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns we need, dropping the rest."""
    available = [col for col in KEEP_COLUMNS if col in df.columns]
    missing = [col for col in KEEP_COLUMNS if col not in df.columns]
    if missing:
        logger.warning(f"Expected columns not found (skipped): {missing}")

    df = df[available].copy()
    logger.info(f"Selected {len(available)} columns: {available}")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with null restaurant_name or location; fill other nulls."""
    initial_len = len(df)

    # Drop rows missing critical fields
    df = df.dropna(subset=["restaurant_name", "location"])
    dropped = initial_len - len(df)
    if dropped > 0:
        logger.warning(f"Dropped {dropped} rows with missing restaurant_name or location")

    # Fill missing cuisines with "Unknown"
    if "cuisines" in df.columns:
        df["cuisines"] = df["cuisines"].fillna("Unknown")

    # Fill missing ratings with 0.0
    if "aggregate_rating" in df.columns:
        df["aggregate_rating"] = df["aggregate_rating"].fillna("0")

    # Fill missing votes with 0
    if "votes" in df.columns:
        df["votes"] = df["votes"].fillna(0)

    return df


def parse_rating(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the 'rate' field which may contain values like '4.1/5', 'NEW', '-', etc.
    """
    if "aggregate_rating" not in df.columns:
        return df

    def _clean_rating(val):
        if pd.isna(val):
            return 0.0
        val = str(val).strip()
        # Handle "4.1/5" format
        if "/" in val:
            val = val.split("/")[0].strip()
        # Handle non-numeric values like "NEW", "-", "nan"
        try:
            rating = float(val)
            return rating
        except (ValueError, TypeError):
            return 0.0

    df["aggregate_rating"] = df["aggregate_rating"].apply(_clean_rating)
    logger.info("Parsed aggregate_rating (handled X/5, NEW, - formats)")
    return df


def parse_numeric_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Convert cost and votes fields to proper numeric types."""
    if "average_cost_for_two" in df.columns:
        # Remove commas from cost strings like "1,500"
        df["average_cost_for_two"] = (
            df["average_cost_for_two"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df["average_cost_for_two"] = pd.to_numeric(
            df["average_cost_for_two"], errors="coerce"
        ).fillna(0.0)
        logger.info("Parsed average_cost_for_two to float")

    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(
            df["votes"], errors="coerce"
        ).fillna(0).astype(int)
        logger.info("Parsed votes to int")

    return df


def standardize_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and standardize text casing."""
    if "restaurant_name" in df.columns:
        df["restaurant_name"] = df["restaurant_name"].astype(str).str.strip()
        # Truncate extremely long names (edge case 1.9)
        df["restaurant_name"] = df["restaurant_name"].str[:200]

    if "location" in df.columns:
        df["location"] = (
            df["location"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    if "city" in df.columns:
        df["city"] = (
            df["city"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    if "cuisines" in df.columns:
        # Normalize separators: /, |, & -> comma (edge case 1.12)
        df["cuisines"] = (
            df["cuisines"]
            .astype(str)
            .str.strip()
            .apply(_normalize_cuisine_separators)
            .str.lower()
            .str[:500]  # Truncate very long cuisine lists (edge case 1.9)
        )

    if "restaurant_type" in df.columns:
        df["restaurant_type"] = (
            df["restaurant_type"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    return df


def _normalize_cuisine_separators(text: str) -> str:
    """Replace /, |, & separators with comma in cuisine strings."""
    normalized = re.sub(r"\s*[/|&]\s*", ", ", text)
    # Collapse multiple commas/spaces
    normalized = re.sub(r",\s*,", ",", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized)
    return normalized.strip(", ")


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate restaurants, keeping the one with highest votes."""
    initial_len = len(df)

    if "votes" in df.columns:
        df = df.sort_values("votes", ascending=False)
        df = df.drop_duplicates(
            subset=["restaurant_name", "location"],
            keep="first"
        )
    else:
        df = df.drop_duplicates(
            subset=["restaurant_name", "location"],
            keep="first"
        )

    removed = initial_len - len(df)
    if removed > 0:
        logger.info(f"Removed {removed} duplicate rows")

    return df.reset_index(drop=True)


def validate_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Clamp rating and cost values to valid ranges."""
    if "aggregate_rating" in df.columns:
        out_of_range = (
            (df["aggregate_rating"] < 0) | (df["aggregate_rating"] > 5)
        ).sum()
        if out_of_range > 0:
            logger.warning(f"Clamping {out_of_range} ratings to [0.0, 5.0]")
        df["aggregate_rating"] = df["aggregate_rating"].clip(0.0, 5.0)

    if "average_cost_for_two" in df.columns:
        negative = (df["average_cost_for_two"] < 0).sum()
        if negative > 0:
            logger.warning(f"Clamping {negative} negative costs to 0")
        outliers = (df["average_cost_for_two"] > 50000).sum()
        if outliers > 0:
            logger.warning(f"Clamping {outliers} extreme costs to 50000")
        df["average_cost_for_two"] = df["average_cost_for_two"].clip(0, 50000)

    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full preprocessing pipeline on a raw Zomato DataFrame.

    Steps:
        1. Normalize & rename column names
        2. Select relevant columns
        3. Handle missing values
        4. Parse rating field (handles "4.1/5", "NEW", "-")
        5. Parse other numeric fields
        6. Standardize text fields
        7. Deduplicate
        8. Validate ranges

    Returns:
        Cleaned DataFrame ready for the recommendation engine.
    """
    logger.info(f"Starting preprocessing -- input shape: {df.shape}")

    df = normalize_columns(df)
    df = select_columns(df)
    df = handle_missing_values(df)
    df = parse_rating(df)
    df = parse_numeric_fields(df)
    df = standardize_text_fields(df)
    df = deduplicate(df)
    df = validate_ranges(df)

    logger.info(f"Preprocessing complete -- output shape: {df.shape}")
    return df
