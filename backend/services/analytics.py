"""
In-memory analytics tracking service.

Thread-safe request analytics for the recommendation API.
Tracks request counts, response times, popular locations/cuisines,
and LLM success/fallback rates.
"""

import time
import threading
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class _AnalyticsStore:
    """Internal analytics data store."""

    # Request metrics
    total_requests: int = 0
    request_times_ms: list = field(default_factory=list)

    # Daily tracking (reset each day)
    _current_day: str = ""
    requests_today: int = 0

    # Popularity tracking
    location_counts: Counter = field(default_factory=Counter)
    cuisine_counts: Counter = field(default_factory=Counter)

    # LLM metrics
    llm_total_calls: int = 0
    llm_fallback_count: int = 0
    llm_times_ms: list = field(default_factory=list)

    # Server start time
    start_time: float = field(default_factory=time.time)


class AnalyticsService:
    """
    Thread-safe analytics service for the recommendation API.

    Tracks per-request metrics and provides aggregate statistics.
    All data is stored in memory and resets on server restart.
    """

    def __init__(self):
        self._store = _AnalyticsStore()
        self._lock = threading.Lock()

    def _check_day_rollover(self):
        """Reset daily counter if the date has changed."""
        today = time.strftime("%Y-%m-%d")
        if today != self._store._current_day:
            self._store._current_day = today
            self._store.requests_today = 0

    def record_request(
        self,
        location: str,
        cuisine: str | None,
        response_time_ms: float,
        used_llm: bool = True,
        llm_fallback: bool = False,
        llm_time_ms: float | None = None,
    ):
        """
        Record a recommendation request with all associated metrics.

        Args:
            location: The location queried.
            cuisine: The cuisine queried (or None).
            response_time_ms: Total response time in milliseconds.
            used_llm: Whether the LLM was invoked.
            llm_fallback: Whether the LLM failed and fallback was used.
            llm_time_ms: Time spent on the LLM call in milliseconds.
        """
        with self._lock:
            self._check_day_rollover()

            self._store.total_requests += 1
            self._store.requests_today += 1
            self._store.request_times_ms.append(response_time_ms)

            # Keep only last 1000 timing samples to avoid unbounded memory
            if len(self._store.request_times_ms) > 1000:
                self._store.request_times_ms = self._store.request_times_ms[-500:]

            # Track popularity
            self._store.location_counts[location.strip().lower()] += 1
            if cuisine:
                for c in cuisine.split(","):
                    c = c.strip().lower()
                    if c:
                        self._store.cuisine_counts[c] += 1

            # LLM metrics
            if used_llm:
                self._store.llm_total_calls += 1
                if llm_fallback:
                    self._store.llm_fallback_count += 1
                if llm_time_ms is not None:
                    self._store.llm_times_ms.append(llm_time_ms)
                    if len(self._store.llm_times_ms) > 1000:
                        self._store.llm_times_ms = self._store.llm_times_ms[-500:]

    def get_stats(self) -> dict:
        """
        Return aggregate analytics as a dictionary.

        Returns:
            Dictionary with request counts, timing, popularity,
            and LLM statistics.
        """
        with self._lock:
            self._check_day_rollover()

            # Average response time
            avg_response_ms = 0.0
            if self._store.request_times_ms:
                avg_response_ms = round(
                    sum(self._store.request_times_ms)
                    / len(self._store.request_times_ms),
                    1,
                )

            # Top locations
            top_locations = [
                {"location": loc.title(), "count": count}
                for loc, count in self._store.location_counts.most_common(10)
            ]

            # Top cuisines
            top_cuisines = [
                {"cuisine": cuisine, "count": count}
                for cuisine, count in self._store.cuisine_counts.most_common(10)
            ]

            # Average LLM time
            avg_llm_ms = 0.0
            if self._store.llm_times_ms:
                avg_llm_ms = round(
                    sum(self._store.llm_times_ms)
                    / len(self._store.llm_times_ms),
                    1,
                )

            return {
                "total_requests": self._store.total_requests,
                "average_response_time_ms": avg_response_ms,
                "requests_today": self._store.requests_today,
                "top_locations": top_locations,
                "top_cuisines": top_cuisines,
                "llm_stats": {
                    "total_calls": self._store.llm_total_calls,
                    "fallback_count": self._store.llm_fallback_count,
                    "success_rate": round(
                        (1 - self._store.llm_fallback_count / max(1, self._store.llm_total_calls))
                        * 100,
                        1,
                    ),
                    "average_llm_time_ms": avg_llm_ms,
                },
            }

    def get_uptime_seconds(self) -> float:
        """Return server uptime in seconds."""
        return round(time.time() - self._store.start_time, 1)

    def reset(self):
        """Reset all analytics data. Useful for development/testing."""
        with self._lock:
            self._store = _AnalyticsStore()


# Module-level singleton
analytics = AnalyticsService()
