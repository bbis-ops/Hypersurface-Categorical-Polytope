"""Cross-process adaptive pacing for the long-running API campaign."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_rate_state(path: str | Path) -> dict[str, Any]:
    return _read(Path(path))


def seconds_until_allowed(path: str | Path, *, now: float | None = None) -> float:
    state = _read(Path(path))
    instant = time.time() if now is None else now
    return max(0.0, float(state.get("next_allowed_epoch", 0.0)) - instant)


def reserve_request(
    path: str | Path, *, base_interval: float, batch_size: int, now: float | None = None
) -> dict[str, Any]:
    """Reserve the next slot so a new child cannot immediately follow this one."""
    target = Path(path)
    instant = time.time() if now is None else now
    state = _read(target)
    interval = max(base_interval, float(state.get("interval_seconds", base_interval)))
    state.update({
        "version": 1,
        "interval_seconds": interval,
        "next_allowed_epoch": max(float(state.get("next_allowed_epoch", 0.0)), instant + interval),
        "last_request_utc": datetime.fromtimestamp(instant, timezone.utc).isoformat(),
        "last_batch_size": batch_size,
        "recommended_batch_size": max(4, int(state.get("recommended_batch_size", batch_size))),
    })
    _write(target, state)
    return state


def note_throttle(
    path: str | Path,
    *,
    base_interval: float,
    batch_size: int,
    retry_after: float | None = None,
    reason: str = "HTTP 429",
    now: float | None = None,
) -> dict[str, Any]:
    target = Path(path)
    instant = time.time() if now is None else now
    state = _read(target)
    streak = int(state.get("consecutive_throttles", 0)) + 1
    prior_interval = max(base_interval, float(state.get("interval_seconds", base_interval)))
    exponential = min(600.0, base_interval * (2.0 ** min(streak, 4)))
    interval = min(600.0, max(prior_interval * 1.5, exponential, retry_after or 0.0))
    prior_batch = int(state.get("recommended_batch_size", batch_size))
    recommended = max(4, min(prior_batch, max(4, (batch_size + 1) // 2)))
    prior_failed_floor = int(state.get("failed_batch_floor", batch_size))
    failed_floor = min(prior_failed_floor, batch_size)
    # A failed size is a measured upper bound, not an invitation to probe it
    # again after a few successes.  Leave at least two candidates of headroom
    # (four for the observed 20-candidate failure).
    recovery_ceiling = max(4, failed_floor - max(2, failed_floor // 5))
    state.update({
        "version": 1,
        "interval_seconds": interval,
        "next_allowed_epoch": max(float(state.get("next_allowed_epoch", 0.0)), instant + interval),
        "consecutive_throttles": streak,
        "success_streak": 0,
        "total_throttles": int(state.get("total_throttles", 0)) + 1,
        "recommended_batch_size": recommended,
        "failed_batch_floor": failed_floor,
        "recovery_batch_ceiling": recovery_ceiling,
        "last_event": "throttle",
        "last_reason": reason,
        "last_event_utc": datetime.fromtimestamp(instant, timezone.utc).isoformat(),
    })
    _write(target, state)
    return state


def note_success(
    path: str | Path,
    *,
    base_interval: float,
    configured_batch_size: int,
    now: float | None = None,
) -> dict[str, Any]:
    target = Path(path)
    instant = time.time() if now is None else now
    state = _read(target)
    # Rate-limit recovery should be deliberately slower than the reaction to a
    # throttle.  A two-percent decay preserves most of the newly learned
    # cooldown instead of racing back to the boundary in three requests.
    interval = max(base_interval, float(state.get("interval_seconds", base_interval)) * 0.98)
    successes = int(state.get("success_streak", 0)) + 1
    recommended = max(4, int(state.get("recommended_batch_size", configured_batch_size)))
    recovery_ceiling = min(
        configured_batch_size,
        max(4, int(state.get("recovery_batch_ceiling", configured_batch_size))),
    )
    if successes >= 8:
        recommended = min(recovery_ceiling, recommended + 2)
        successes = 0
    successful_batch = int(state.get("last_batch_size", recommended))
    state.update({
        "version": 1,
        "interval_seconds": interval,
        "next_allowed_epoch": instant + interval,
        "consecutive_throttles": 0,
        "success_streak": successes,
        "total_successes": int(state.get("total_successes", 0)) + 1,
        "recommended_batch_size": recommended,
        "largest_successful_batch": max(
            successful_batch, int(state.get("largest_successful_batch", 0))
        ),
        "last_event": "success",
        "last_reason": "",
        "last_event_utc": datetime.fromtimestamp(instant, timezone.utc).isoformat(),
    })
    _write(target, state)
    return state
