"""
Queue wait-time estimator.
Uses a simple documented formula:
  estimated_wait = (waiting_count / max(active_windows, 1)) * avg_service_minutes
Baseline: 12 minutes average service duration per transaction.
"""
from __future__ import annotations

AVG_SERVICE_MINUTES = 12
DEFAULT_ACTIVE_WINDOWS = 3


def estimate_wait(waiting_count: int, in_service_count: int) -> int | None:
    """
    Returns estimated wait in minutes, or None if queue data is unavailable.
    active_windows is inferred from in_service_count (at least 1 assumed if any are in service).
    """
    if waiting_count == 0:
        return 0

    active_windows = max(in_service_count, 1) if in_service_count >= 0 else DEFAULT_ACTIVE_WINDOWS
    wait = (waiting_count / active_windows) * AVG_SERVICE_MINUTES
    return max(1, round(wait))
