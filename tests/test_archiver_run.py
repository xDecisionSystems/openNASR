"""One archiver pass: staging through outages and de-duplicated alerts."""

from datetime import date, datetime, timezone

import pytest

from openNASR.cycles import CycleManager, RemoteCycle
from openNASR_archiver import run_once
from openNASR_contract import LocalBucket
from openNASR_archiver import run as run_module

FIXTURE = "schema_only/nasr_2026_09"
CYCLE = date(2026, 9, 3)


class RecordingNotifier:
    def __init__(self):
        self.events = []

    def notify(self, kind, state, message):
        self.events.append((kind, state))


class FakeProvider:
    def __init__(self, effective_date=CYCLE, error=None):
        self.effective_date = effective_date
        self.error = error

    def discover(self):
        if self.error:
            raise self.error
        return RemoteCycle(self.effective_date, "https://example.invalid/x.zip")


@pytest.fixture
def setup(make_nasr_from_fixture, tmp_path):
    _, cache_root = make_nasr_from_fixture(FIXTURE)
    manager = CycleManager(cache_root, provider=FakeProvider())
    return manager, LocalBucket(tmp_path / "bucket"), tmp_path / "state.json"


SOON = datetime(2026, 9, 10, tzinfo=timezone.utc)


def _run(setup, notifier, **options):
    manager, bucket, state = setup
    options.setdefault("now", lambda: SOON)
    return run_once(
        manager, bucket, state, notifier=notifier, required_tables=(), **options
    )


def test_a_pass_publishes_a_cycle_already_in_the_cache(setup):
    notifier = RecordingNotifier()

    first = _run(setup, notifier)
    second = _run(setup, notifier)

    assert (first.status, second.status) == ("published", "already_published")
    assert notifier.events == []


def test_a_bucket_outage_alerts_once_and_resolves_once_without_losing_work(setup):
    manager, bucket, _ = setup
    notifier = RecordingNotifier()
    real_put_file = bucket.put_file

    def down(*args, **kwargs):
        raise OSError("bucket unreachable")

    bucket.put_file = down
    outcomes = [_run(setup, notifier) for _ in range(3)]
    bucket.put_file = real_put_file
    recovered = _run(setup, notifier)

    assert [o.kind for o in outcomes] == [run_module.BUCKET_UNAVAILABLE] * 3
    assert recovered.status == "published"
    assert notifier.events == [
        (run_module.BUCKET_UNAVAILABLE, "firing"),
        (run_module.BUCKET_UNAVAILABLE, "resolved"),
    ]


def test_faa_being_unreachable_is_reported_and_publishes_nothing(setup):
    manager, bucket, _ = setup
    manager.provider = FakeProvider(error=OSError("FAA site down"))
    notifier = RecordingNotifier()

    outcome = _run(setup, notifier)

    assert outcome.kind == run_module.SOURCE_UNAVAILABLE
    assert list(bucket.list_keys()) == []
    assert notifier.events == [(run_module.SOURCE_UNAVAILABLE, "firing")]


def test_a_build_that_fails_validation_is_reported_and_not_published(setup):
    notifier = RecordingNotifier()
    manager, bucket, state = setup

    outcome = run_once(
        manager,
        bucket,
        state,
        notifier=notifier,
        required_tables=("NO_SUCH_TABLE",),
    )

    assert outcome.kind == run_module.VALIDATION_FAILED
    assert list(bucket.list_keys()) == []


def test_no_new_cycle_alert_fires_after_the_grace_period_and_clears(setup):
    notifier = RecordingNotifier()
    _run(setup, notifier)
    assert notifier.events == []

    # The cycle is 2026-09-03; 28 days + 3 days of grace ends 2026-10-04.
    late = datetime(2026, 10, 10, tzinfo=timezone.utc)
    _run(setup, notifier, now=lambda: late)
    _run(setup, notifier, now=lambda: late)
    assert notifier.events == [(run_module.NO_NEW_CYCLE, "firing")]

    _run(setup, notifier)  # clock back within the window
    assert notifier.events[-1] == (run_module.NO_NEW_CYCLE, "resolved")


def test_alert_state_survives_a_restart(setup):
    notifier = RecordingNotifier()
    manager, bucket, state = setup
    manager.provider = FakeProvider(error=OSError("down"))
    _run(setup, notifier)

    restarted = RecordingNotifier()
    _run(setup, restarted)

    assert restarted.events == []  # already announced before the restart
