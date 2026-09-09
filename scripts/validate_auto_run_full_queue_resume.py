from __future__ import annotations

import re
from datetime import datetime
from typing import Any

SCHEMA = "rozkalns.auto-run-full-queue-resume-signal.v1"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

SIGNAL_FIELDS = {
    "schema",
    "repository",
    "repository_id",
    "source",
    "event_name",
    "event_action",
    "delivery_id",
    "observed_at",
    "target_issue_number",
    "target_pr_number",
}

SOURCES = {
    "GITHUB_EVENT",
    "WATCHDOG",
    "MANUAL_CONTINUATION",
}

EVENT_ALLOWLIST = {
    "issues",
    "issue_comment",
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "check_suite",
    "check_run",
    "status",
    "push",
}

QUEUE_STATES = {
    "READY",
    "ACTIVE",
    "PAUSED",
    "QUEUE_SOURCE_COMPLETE",
    "STOPPED",
}


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _is_optional_positive_int(value: Any) -> bool:
    return value is None or _is_positive_int(value)


def _is_optional_bounded_string(value: Any, maximum: int) -> bool:
    return value is None or (isinstance(value, str) and 1 <= len(value) <= maximum)


def _is_offset_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_signal(signal: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(signal, dict):
        return ["signal must be an object"]

    if set(signal) != SIGNAL_FIELDS:
        return ["signal keys mismatch"]

    if signal["schema"] != SCHEMA:
        errors.append("schema mismatch")

    repository = signal["repository"]
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        errors.append("repository format is invalid")

    if not _is_positive_int(signal["repository_id"]):
        errors.append("repository_id must be a positive integer")

    source = signal["source"]
    if source not in SOURCES:
        errors.append("source is invalid")

    event_name = signal["event_name"]
    if not isinstance(event_name, str) or not 1 <= len(event_name) <= 64:
        errors.append("event_name is invalid")

    if not _is_optional_bounded_string(signal["event_action"], 64):
        errors.append("event_action is invalid")

    if not _is_optional_bounded_string(signal["delivery_id"], 128):
        errors.append("delivery_id is invalid")

    if not _is_offset_datetime(signal["observed_at"]):
        errors.append("observed_at must be an offset-aware ISO-8601 datetime")

    if not _is_optional_positive_int(signal["target_issue_number"]):
        errors.append("target_issue_number is invalid")

    if not _is_optional_positive_int(signal["target_pr_number"]):
        errors.append("target_pr_number is invalid")

    if source == "GITHUB_EVENT":
        if event_name not in EVENT_ALLOWLIST:
            errors.append("GitHub event is not allowlisted")
    elif source == "WATCHDOG":
        if event_name != "watchdog":
            errors.append("watchdog source must use watchdog event_name")
        if signal["event_action"] is not None:
            errors.append("watchdog source must not carry event_action")
        if signal["delivery_id"] is not None:
            errors.append("watchdog source must not carry delivery_id")
        if signal["target_issue_number"] is not None or signal["target_pr_number"] is not None:
            errors.append("watchdog source must not carry target issue or PR")
    elif source == "MANUAL_CONTINUATION":
        if event_name != "manual_continuation":
            errors.append("manual continuation must use manual_continuation event_name")
        if signal["event_action"] is not None:
            errors.append("manual continuation must not carry event_action")
        if signal["delivery_id"] is not None:
            errors.append("manual continuation must not carry delivery_id")

    return errors


def delivery_dedupe_key(signal: dict[str, Any]) -> str | None:
    if validate_signal(signal):
        return None
    if signal["source"] != "GITHUB_EVENT" or signal["delivery_id"] is None:
        return None
    return f"github-delivery:{signal['delivery_id']}"


def event_may_wake(
    signal: dict[str, Any],
    *,
    expected_repository: str,
    expected_repository_id: int,
) -> bool:
    if validate_signal(signal):
        return False
    if signal["repository"] != expected_repository:
        return False
    if signal["repository_id"] != expected_repository_id:
        return False
    return True


def decide_after_canonical_refresh(
    *,
    queue_state: str,
    signal_relevant: bool,
    canonical_refresh_complete: bool,
    authority_valid: bool,
    scope_rules_main_valid: bool,
    owner_gate_required: bool,
) -> str:
    """Return a resume disposition after fresh canonical GitHub retrieval.

    This helper deliberately accepts no cursor, issue order, PR head, merge result,
    or event payload facts that could advance controller state. The caller must
    re-read and validate those facts through the A2/A3 contracts.
    """
    if not signal_relevant:
        return "IGNORE"
    if not canonical_refresh_complete:
        return "STOP_CANONICAL_REFRESH_INCOMPLETE"
    if queue_state not in QUEUE_STATES:
        return "STOP_QUEUE_STATE_INVALID"
    if queue_state == "STOPPED":
        return "STOPPED_NO_AUTO_RESUME"
    if owner_gate_required:
        return "OWNER_GATE_NO_AUTO_RESUME"
    if queue_state == "READY":
        return "NOOP_NOT_ACTIVATED"
    if not authority_valid or not scope_rules_main_valid:
        return "STOP_REVALIDATION_FAILED"
    if queue_state in {"ACTIVE", "PAUSED"}:
        return "RESUME_ACTIVE_ITEM"
    if queue_state == "QUEUE_SOURCE_COMPLETE":
        return "READ_ONLY_FINAL_RECONCILE"
    return "STOP_QUEUE_STATE_INVALID"
