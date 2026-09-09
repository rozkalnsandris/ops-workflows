#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

SCHEMA = "rozkalns.auto-run-full-queue-controller-state.v1"
QUEUE_STATES = {"READY", "ACTIVE", "PAUSED", "QUEUE_SOURCE_COMPLETE", "STOPPED"}
ITEM_STATES = {"PENDING", "ACTIVE", "SOURCE_COMPLETE", "STOPPED"}
TOP_LEVEL_FIELDS = {
    "schema",
    "repository",
    "queue_id",
    "frozen_issues",
    "cursor",
    "state",
    "active_issue",
    "items",
}
ITEM_FIELDS = {"issue", "state", "terminal_evidence"}
EVIDENCE_FIELDS = {"pr_number", "merged_head_sha", "exact_main_sha", "exact_main_ci"}
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _is_uuid4(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value.lower()


def validate_terminal_evidence(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["terminal_evidence must be an object"]
    if set(value) != EVIDENCE_FIELDS:
        errors.append("terminal_evidence keys mismatch")
        return errors
    if not isinstance(value["pr_number"], int) or isinstance(value["pr_number"], bool) or value["pr_number"] < 1:
        errors.append("terminal_evidence.pr_number must be a positive integer")
    for key in ("merged_head_sha", "exact_main_sha"):
        if not isinstance(value[key], str) or SHA_RE.fullmatch(value[key]) is None:
            errors.append(f"terminal_evidence.{key} must be lowercase 40-hex")
    if value["exact_main_ci"] != "PASS":
        errors.append("terminal_evidence.exact_main_ci must equal PASS")
    return errors


def validate_snapshot(snapshot: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(snapshot, dict):
        return ["snapshot must be an object"]
    if set(snapshot) != TOP_LEVEL_FIELDS:
        return ["snapshot keys mismatch"]

    if snapshot["schema"] != SCHEMA:
        errors.append("snapshot schema mismatch")
    if not isinstance(snapshot["repository"], str) or REPOSITORY_RE.fullmatch(snapshot["repository"]) is None:
        errors.append("repository must be owner/name")
    if not _is_uuid4(snapshot["queue_id"]):
        errors.append("queue_id must be canonical UUIDv4")

    issues = snapshot["frozen_issues"]
    if not isinstance(issues, list) or not 1 <= len(issues) <= 10:
        errors.append("frozen_issues length must be between 1 and 10")
        issues = []
    else:
        if any(not isinstance(issue, int) or isinstance(issue, bool) or issue < 1 for issue in issues):
            errors.append("frozen_issues must contain positive integers")
        if len(set(issues)) != len(issues):
            errors.append("frozen_issues must be unique")

    state = snapshot["state"]
    if state not in QUEUE_STATES:
        errors.append("unknown queue state")

    cursor = snapshot["cursor"]
    if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
        errors.append("cursor must be a non-negative integer")
        cursor = -1

    active_issue = snapshot["active_issue"]
    if active_issue is not None and (
        not isinstance(active_issue, int) or isinstance(active_issue, bool) or active_issue < 1
    ):
        errors.append("active_issue must be a positive integer or null")

    items = snapshot["items"]
    if not isinstance(items, list):
        errors.append("items must be an array")
        items = []
    if issues and len(items) != len(issues):
        errors.append("items length must equal frozen_issues length")

    normalized_item_states: list[str | None] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
            errors.append(f"items[{index}] keys mismatch")
            normalized_item_states.append(None)
            continue
        issue = item["issue"]
        item_state = item["state"]
        evidence = item["terminal_evidence"]
        if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
            errors.append(f"items[{index}].issue must be a positive integer")
        if index < len(issues) and issue != issues[index]:
            errors.append(f"items[{index}].issue must preserve frozen order")
        if item_state not in ITEM_STATES:
            errors.append(f"items[{index}].state is invalid")
            normalized_item_states.append(None)
        else:
            normalized_item_states.append(item_state)
        if item_state == "SOURCE_COMPLETE":
            errors.extend(f"items[{index}]: {error}" for error in validate_terminal_evidence(evidence))
        elif evidence is not None:
            errors.append(f"items[{index}].terminal_evidence must be null unless SOURCE_COMPLETE")

    if issues and cursor > len(issues):
        errors.append("cursor cannot exceed queue length")

    if state == "READY" and issues:
        if cursor != 0:
            errors.append("READY cursor must be zero")
        if active_issue is not None:
            errors.append("READY active_issue must be null")
        if any(item_state != "PENDING" for item_state in normalized_item_states):
            errors.append("READY requires every item PENDING")

    if state in {"ACTIVE", "PAUSED"} and issues:
        if not 0 <= cursor < len(issues):
            errors.append(f"{state} cursor must point inside frozen_issues")
        else:
            if active_issue != issues[cursor]:
                errors.append(f"{state} active_issue must equal frozen_issues[cursor]")
            for index, item_state in enumerate(normalized_item_states):
                expected = "SOURCE_COMPLETE" if index < cursor else "ACTIVE" if index == cursor else "PENDING"
                if item_state != expected:
                    errors.append(f"{state} item state mismatch at index {index}: expected {expected}")

    if state == "QUEUE_SOURCE_COMPLETE" and issues:
        if cursor != len(issues):
            errors.append("QUEUE_SOURCE_COMPLETE cursor must equal queue length")
        if active_issue is not None:
            errors.append("QUEUE_SOURCE_COMPLETE active_issue must be null")
        if any(item_state != "SOURCE_COMPLETE" for item_state in normalized_item_states):
            errors.append("QUEUE_SOURCE_COMPLETE requires every item SOURCE_COMPLETE")

    if state == "STOPPED" and issues:
        if not 0 <= cursor < len(issues):
            errors.append("STOPPED cursor must point to stopped issue")
        else:
            if active_issue != issues[cursor]:
                errors.append("STOPPED active_issue must equal frozen_issues[cursor]")
            for index, item_state in enumerate(normalized_item_states):
                expected = "SOURCE_COMPLETE" if index < cursor else "STOPPED" if index == cursor else "PENDING"
                if item_state != expected:
                    errors.append(f"STOPPED item state mismatch at index {index}: expected {expected}")

    return errors


def _validated_copy(snapshot: dict[str, Any]) -> dict[str, Any]:
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("; ".join(errors))
    return copy.deepcopy(snapshot)


def make_ready(repository: str, frozen_issues: list[int], queue_id: str) -> dict[str, Any]:
    snapshot = {
        "schema": SCHEMA,
        "repository": repository,
        "queue_id": queue_id,
        "frozen_issues": list(frozen_issues),
        "cursor": 0,
        "state": "READY",
        "active_issue": None,
        "items": [
            {"issue": issue, "state": "PENDING", "terminal_evidence": None}
            for issue in frozen_issues
        ],
    }
    return _validated_copy(snapshot)


def activate(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _validated_copy(snapshot)
    if result["state"] != "READY":
        raise ValueError("activate requires READY state")
    result["state"] = "ACTIVE"
    result["cursor"] = 0
    result["active_issue"] = result["frozen_issues"][0]
    result["items"][0]["state"] = "ACTIVE"
    return _validated_copy(result)


def pause(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _validated_copy(snapshot)
    if result["state"] != "ACTIVE":
        raise ValueError("pause requires ACTIVE state")
    result["state"] = "PAUSED"
    return _validated_copy(result)


def resume(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _validated_copy(snapshot)
    if result["state"] != "PAUSED":
        raise ValueError("resume requires PAUSED state")
    result["state"] = "ACTIVE"
    return _validated_copy(result)


def stop(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _validated_copy(snapshot)
    if result["state"] not in {"ACTIVE", "PAUSED"}:
        raise ValueError("stop requires ACTIVE or PAUSED state")
    index = result["cursor"]
    result["state"] = "STOPPED"
    result["items"][index]["state"] = "STOPPED"
    result["items"][index]["terminal_evidence"] = None
    return _validated_copy(result)


def advance_after_source_complete(
    snapshot: dict[str, Any], terminal_evidence: dict[str, Any]
) -> dict[str, Any]:
    result = _validated_copy(snapshot)
    if result["state"] != "ACTIVE":
        raise ValueError("advance requires ACTIVE state")
    evidence_errors = validate_terminal_evidence(terminal_evidence)
    if evidence_errors:
        raise ValueError("; ".join(evidence_errors))

    index = result["cursor"]
    result["items"][index]["state"] = "SOURCE_COMPLETE"
    result["items"][index]["terminal_evidence"] = copy.deepcopy(terminal_evidence)

    next_index = index + 1
    if next_index == len(result["frozen_issues"]):
        result["cursor"] = next_index
        result["state"] = "QUEUE_SOURCE_COMPLETE"
        result["active_issue"] = None
    else:
        result["cursor"] = next_index
        result["state"] = "ACTIVE"
        result["active_issue"] = result["frozen_issues"][next_index]
        result["items"][next_index]["state"] = "ACTIVE"
    return _validated_copy(result)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} SNAPSHOT.json", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"QUEUE_STATE_INVALID: {exc}", file=sys.stderr)
        return 1
    errors = validate_snapshot(snapshot)
    if errors:
        for error in errors:
            print(f"QUEUE_STATE_INVALID: {error}", file=sys.stderr)
        return 1
    print("QUEUE_STATE_VALID=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
