"""One archiver pass: discover, download, publish, and keep alerts quiet.

The local cache is the staging area. A bucket outage therefore costs nothing:
the archive and the built database stay in the cache and the next pass
publishes them. Alerts are de-duplicated through a small state file: a
problem is announced once when it starts and once when it ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Callable, Protocol

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import DuckDbBuildError
from openNASR.exceptions import DownloadError

from openNASR_contract import Bucket
from .backfill import BackfillResult, _one, next_cycle_after
from .publish import BUILDER_VERSION, PublishError, PublishResult, publish_cycle

CYCLE_DAYS = 28
LOGGER = logging.getLogger("openNASR_archiver")

SOURCE_UNAVAILABLE = "source_unavailable"
VALIDATION_FAILED = "validation_failed"
BUILD_FAILED = "build_failed"
BUCKET_UNAVAILABLE = "bucket_unavailable"
NO_NEW_CYCLE = "no_new_cycle"
UPCOMING_FAILED = "upcoming_cycle_failed"


class Notifier(Protocol):
    def notify(self, kind: str, state: str, message: str) -> None:
        """``state`` is ``"firing"`` or ``"resolved"``."""


class LogNotifier:
    def notify(self, kind: str, state: str, message: str) -> None:
        level = logging.ERROR if state == "firing" else logging.INFO
        LOGGER.log(level, "[%s] %s: %s", state, kind, message)


class WebhookNotifier:
    """Post alerts as ``{"text": ...}`` JSON (Slack-compatible)."""

    def __init__(self, url: str, *, opener=None) -> None:
        self.url = url
        self._opener = opener

    def notify(self, kind: str, state: str, message: str) -> None:
        import urllib.request

        icon = ":rotating_light:" if state == "firing" else ":white_check_mark:"
        body = json.dumps(
            {"text": f"{icon} openNASR archiver [{state}] {kind}: {message}"}
        )
        request = urllib.request.Request(
            self.url,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            (self._opener or urllib.request.urlopen)(request, timeout=10).close()
        except Exception:  # an alert that cannot be delivered must not stop a pass
            LOGGER.exception("could not deliver alert %s", kind)


class CompositeNotifier:
    def __init__(self, *notifiers: Notifier) -> None:
        self.notifiers = notifiers

    def notify(self, kind: str, state: str, message: str) -> None:
        for notifier in self.notifiers:
            notifier.notify(kind, state, message)


@dataclass(frozen=True)
class RunOutcome:
    status: str  # published | already_published | failed
    effective_date: date | None
    kind: str | None = None
    detail: str = ""


class AlertState:
    """Which alerts are active, persisted so restarts do not re-announce."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        self.data.setdefault("active", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, sort_keys=True))
        temporary.replace(self.path)

    @property
    def last_published(self) -> date | None:
        value = self.data.get("last_published")
        return date.fromisoformat(value) if value else None


def run_once(
    manager: CycleManager,
    bucket: Bucket,
    state_path: Path,
    *,
    notifier: Notifier | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    grace_days: int = 3,
    **publish_options,
) -> RunOutcome:
    notifier = notifier or LogNotifier()
    state = AlertState(state_path)
    outcome = _attempt(manager, bucket, state, **publish_options)
    if outcome.status == "failed":
        _fire(state, notifier, outcome.kind or "failed", outcome.detail)
    else:
        for kind in (
            SOURCE_UNAVAILABLE,
            VALIDATION_FAILED,
            BUILD_FAILED,
            BUCKET_UNAVAILABLE,
        ):
            _resolve(state, notifier, kind)
        _check_overdue(state, notifier, now(), grace_days, outcome)
        _handle_upcoming(manager, bucket, state, notifier, outcome, publish_options)
    state.save()
    return outcome


def _attempt(manager, bucket, state, **publish_options) -> RunOutcome:
    try:
        remote = manager.provider.discover()
        effective_date = remote.effective_date
    except Exception as error:
        return RunOutcome("failed", None, SOURCE_UNAVAILABLE, f"discovery: {error}")
    try:
        manager.download(effective_date)
    except (DownloadError, OSError, ValueError) as error:
        return RunOutcome("failed", effective_date, SOURCE_UNAVAILABLE, str(error))
    try:
        result: PublishResult = publish_cycle(
            manager, effective_date, bucket, **publish_options
        )
    except PublishError as error:
        return RunOutcome("failed", effective_date, VALIDATION_FAILED, str(error))
    except DuckDbBuildError as error:
        return RunOutcome("failed", effective_date, BUILD_FAILED, str(error))
    except Exception as error:  # the bucket (network, credentials, ...)
        return RunOutcome("failed", effective_date, BUCKET_UNAVAILABLE, str(error))
    state.data["last_published"] = effective_date.isoformat()
    return RunOutcome(
        "already_published" if result.already_published else "published",
        effective_date,
    )


def _upcoming(manager, bucket, current: date, publish_options) -> BackfillResult:
    """Publish the cycle after ``current``, which the FAA posts ~20 days early."""

    upcoming = next_cycle_after(current)
    return _one(
        manager, bucket, upcoming, BUILDER_VERSION, False, set(), publish_options
    )


def _handle_upcoming(
    manager, bucket, state, notifier, outcome, publish_options
) -> None:
    """Best effort: not being posted yet is normal; a build that fails is not."""

    if outcome.effective_date is None:
        return
    result = _upcoming(manager, bucket, outcome.effective_date, publish_options)
    if result.status == "failed":
        _fire(
            state,
            notifier,
            UPCOMING_FAILED,
            f"{result.effective_date}: {result.detail}",
        )
    else:
        _resolve(state, notifier, UPCOMING_FAILED)


def _check_overdue(state, notifier, today, grace_days, outcome) -> None:
    last = state.last_published
    if last is None:
        return
    due = last + timedelta(days=CYCLE_DAYS + grace_days)
    if today.date() > due:
        _fire(
            state,
            notifier,
            NO_NEW_CYCLE,
            f"no cycle newer than {last.isoformat()} was published "
            f"by {due.isoformat()}",
        )
    else:
        _resolve(state, notifier, NO_NEW_CYCLE)


def _fire(state, notifier, kind: str, message: str) -> None:
    if kind in state.data["active"]:
        return
    state.data["active"][kind] = message
    notifier.notify(kind, "firing", message)


def _resolve(state, notifier, kind: str) -> None:
    if state.data["active"].pop(kind, None) is not None:
        notifier.notify(kind, "resolved", f"{kind} has cleared")
