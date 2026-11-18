"""Publish a range of historical (or upcoming) cycles."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import DuckDbBuildError
from openNASR.exceptions import DownloadError
from openNASR_contract import Bucket, list_builds

from .publish import BUILDER_VERSION, PublishError, publish_cycle

CYCLE_DAYS = 28
ANCHOR = date(2026, 10, 29)
"""A known effective date; every cycle falls a multiple of 28 days from it."""


@dataclass(frozen=True)
class BackfillResult:
    effective_date: date
    status: str  # published | already_published | unavailable | failed
    detail: str = ""


def cycle_dates(start: date, end: date) -> list[date]:
    """Effective dates on the 28-day grid within ``[start, end]``."""

    first = start + timedelta(days=(-(start - ANCHOR).days) % CYCLE_DAYS)
    dates = []
    current = first
    while current <= end:
        dates.append(current)
        current += timedelta(days=CYCLE_DAYS)
    return dates


def next_cycle_after(today: date) -> date:
    return cycle_dates(today + timedelta(days=1), today + timedelta(days=CYCLE_DAYS))[0]


def backfill(
    manager: CycleManager,
    bucket: Bucket,
    dates: list[date],
    *,
    builder: int = BUILDER_VERSION,
    force: bool = False,
    progress: Callable[[BackfillResult], None] = lambda result: None,
    **publish_options,
) -> list[BackfillResult]:
    """Publish each date in turn; one failure never stops the others."""

    published = {m.effective_date for m in list_builds(bucket) if m.builder == builder}
    results = []
    for effective_date in dates:
        result = _one(
            manager, bucket, effective_date, builder, force, published, publish_options
        )
        results.append(result)
        progress(result)
    return results


def _one(manager, bucket, effective_date, builder, force, published, options):
    if effective_date.isoformat() in published and not force:
        return BackfillResult(effective_date, "already_published")
    try:
        manager.download(effective_date)
    except (DownloadError, ValueError, OSError) as error:
        return BackfillResult(effective_date, "unavailable", str(error))
    try:
        outcome = publish_cycle(
            manager, effective_date, bucket, builder=builder, **options
        )
    except DownloadError as error:
        return BackfillResult(effective_date, "unavailable", str(error))
    except (PublishError, DuckDbBuildError) as error:
        return BackfillResult(effective_date, "failed", str(error))
    except Exception as error:  # the bucket
        return BackfillResult(effective_date, "failed", f"bucket: {error}")
    return BackfillResult(
        effective_date,
        "already_published" if outcome.already_published else "published",
    )
