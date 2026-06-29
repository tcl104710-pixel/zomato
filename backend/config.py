"""
Application configuration.

Loads settings from .env file using python-dotenv.
All settings have sensible defaults except GROQ_API_KEY.
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE)


def _parse_float(value: str, min_val: float, max_val: float, default: float) -> float:
    """Parse a float from string, clamping to [min_val, max_val]."""
    try:
        parsed = float(value)
        if parsed < min_val or parsed > max_val:
            logger.warning(
                f"Value {parsed} out of range [{min_val}, {max_val}], clamping."
            )
            return max(min_val, min(parsed, max_val))
        return parsed
    except (ValueError, TypeError):
        return default


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Groq LLM
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.LLM_TEMPERATURE: float = _parse_float(
            os.getenv("LLM_TEMPERATURE", "0.4"), 0.0, 2.0, 0.4
        )
        self.LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

        # Data
        self.DATA_PATH: str = os.getenv("DATA_PATH", "data/processed/zomato_cleaned.csv")

        # Recommendation settings
        self.TOP_N_RESULTS: int = int(os.getenv("TOP_N_RESULTS", "5"))
        self.MAX_SHORTLIST: int = max(1, int(os.getenv("MAX_SHORTLIST", "20")))

        # Budget mapping (Rs for two)
        self.BUDGET_RANGES: dict = {
            "low": (0, 500),
            "medium": (501, 1500),
            "high": (1501, 50000),
        }

        # --- Post-init validation ---

        # Ensure TOP_N_RESULTS <= MAX_SHORTLIST
        if self.TOP_N_RESULTS > self.MAX_SHORTLIST:
            logger.warning(
                f"TOP_N_RESULTS ({self.TOP_N_RESULTS}) > MAX_SHORTLIST "
                f"({self.MAX_SHORTLIST}). Adjusting TOP_N_RESULTS."
            )
            self.TOP_N_RESULTS = self.MAX_SHORTLIST

        # Resolve DATA_PATH relative to project root
        data_path = Path(self.DATA_PATH)
        if not data_path.is_absolute():
            data_path = PROJECT_ROOT / data_path
        self.DATA_PATH = str(data_path)


settings = Settings()
