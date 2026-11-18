"""Backfilling a range of cycles."""

from datetime import date

import pytest

from openNASR.cycles import CycleManager
from openNASR_archiver import backfill, cycle_dates, next_cycle_after
from openNASR_contract import LocalBucket

FIXTURE = "schema_only/nasr_2026_09"
CYCLE = date(2026, 9, 3)


def test_cycle_dates_follow_the_28_day_grid():
    assert cycle_dates(date(2026, 8, 1), date(2026, 11, 30)) == [
        date(2026, 8, 6),
        date(2026, 9, 3),
        date(2026, 10, 1),
        date(2026, 10, 29),
        date(2026, 11, 26),
    ]
    assert cycle_dates(date(2026, 9, 4), date(2026, 9, 30)) == []
    assert cycle_dates(date(2026, 9, 3), date(2026, 9, 3)) == [CYCLE]
    assert next_cycle_after(date(2026, 11, 16)) == date(2026, 11, 26)
    assert next_cycle_after(date(2026, 11, 26)) == date(2026, 12, 24)


class OfflineProvider:
    """Only the cached cycle is available; any other date is unavailable."""

    def for_date(self, effective_date):
        raise ValueError(f"FAA has no cycle {effective_date}")

    def discover(self):
        raise ValueError("offline")


@pytest.fixture
def setup(make_nasr_from_fixture, tmp_path):
    _, cache_root = make_nasr_from_fixture(FIXTURE)
    manager = CycleManager(cache_root, provider=OfflineProvider())
    return manager, LocalBucket(tmp_path / "bucket")


def test_backfill_reports_each_cycle_and_does_not_stop_on_a_missing_one(setup):
    manager, bucket = setup
    seen = []

    results = backfill(
        manager,
        bucket,
        [date(2026, 8, 6), CYCLE, date(2026, 10, 1)],
        builder=1,
        required_tables=(),
        progress=seen.append,
    )

    assert [(r.effective_date, r.status) for r in results] == [
        (date(2026, 8, 6), "unavailable"),
        (CYCLE, "published"),
        (date(2026, 10, 1), "unavailable"),
    ]
    assert seen == results


def test_backfill_skips_published_cycles_without_downloading(setup):
    manager, bucket = setup
    backfill(manager, bucket, [CYCLE], builder=1, required_tables=())

    class Exploding(OfflineProvider):
        def for_date(self, effective_date):
            raise AssertionError("must not contact the FAA for a published cycle")

    manager.provider = Exploding()
    (result,) = backfill(manager, bucket, [CYCLE], builder=1, required_tables=())

    assert result.status == "already_published"


def test_a_cycle_that_fails_validation_is_reported_failed(setup):
    manager, bucket = setup

    (result,) = backfill(
        manager, bucket, [CYCLE], builder=1, required_tables=("NO_SUCH",)
    )

    assert result.status == "failed"
    assert "required tables" in result.detail
    assert list(bucket.list_keys()) == []
