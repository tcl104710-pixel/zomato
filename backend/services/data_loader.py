"""
Dataset loading and caching service.

Loads the preprocessed Zomato CSV into memory and provides query helpers.
The DataFrame is loaded once at startup and cached as a module-level singleton.
"""

import logging
from pathlib import Path

import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

# Module-level cache
_dataframe: pd.DataFrame | None = None


def load_data() -> pd.DataFrame:
    """
    Load the cleaned Zomato CSV into a Pandas DataFrame.

    Caches the result in memory so subsequent calls return the same object.
    Raises FileNotFoundError if the CSV does not exist.
    """
    global _dataframe

    if _dataframe is not None:
        return _dataframe

    data_path = Path(settings.DATA_PATH)
    if not data_path.exists():
        logger.error(f"Dataset not found at {data_path}")
        raise FileNotFoundError(
            f"Cleaned dataset not found at '{data_path}'. "
            "Run 'python scripts/ingest.py' first to download and preprocess the data."
        )

    logger.info(f"Loading dataset from {data_path}")
    _dataframe = pd.read_csv(data_path)
    logger.info(f"Dataset loaded: {_dataframe.shape[0]} rows, {_dataframe.shape[1]} columns")

    return _dataframe


def get_dataframe() -> pd.DataFrame:
    """Get the cached DataFrame, loading it if necessary."""
    return load_data()


def get_unique_locations() -> list[str]:
    """Return sorted list of unique locations in the dataset."""
    df = get_dataframe()
    locations = df["location"].dropna().unique().tolist()
    return sorted(locations)


def get_unique_cuisines() -> list[str]:
    """
    Return sorted list of unique individual cuisines in the dataset.

    Since restaurants can have multiple comma-separated cuisines,
    this splits and deduplicates them.
    """
    df = get_dataframe()
    all_cuisines = set()
    for cuisines_str in df["cuisines"].dropna():
        for cuisine in str(cuisines_str).split(","):
            cuisine = cuisine.strip()
            if cuisine and cuisine.lower() != "unknown":
                all_cuisines.add(cuisine)

    return sorted(all_cuisines)


def reload_data() -> pd.DataFrame:
    """Force reload the dataset from disk (useful after re-ingestion)."""
    global _dataframe
    _dataframe = None
    return load_data()
