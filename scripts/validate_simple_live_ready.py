#!/usr/bin/env python3
"""Pure source validator for the Simple LIVE v1 ready envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

SCHEMA = "rozkalns.simple-live-ready.v1"
CLASSIFICATION = "OWNER_LIVE_REQUIRED"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
OPERATION = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MUTATION_CLASS = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
BASELINE_KINDS = {"EXACT_SHA", "VERSION_ID", "DEPLOYMENT_ID", "HOST_STATE", "OTHER", "UNAVAILABLE"}
TOP_LEVEL_KEYS = {
    "schema",
    "classification",
    "queue_id",
    "source_repository",
    "source_sha",
    "target_alias",
    "operation_id",
    "operation_contract_digest_sha256",
    "consumer_rules_digest_sha256",
    "shared_contract_sha",
    "expected_baseline",
    "read_only_preflight_digest_sha256",
    "allowed_mutation_classes",
    "maximum_total_mutations",
    "exclusions",
}


class ValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def binding_sha256(payload: dict[str, Any]) -> str:
    validate_ready(payload)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def owner_command(payload: dict[str, Any]) -> str:
    return f"LIVE {binding_sha256(payload)}"


def validate_ready(payload: dict[str, Any]) -> None:
    _require(isinstance(payload, dict), "payload must be an object")
    _require(set(payload) == TOP_LEVEL_KEYS, "top-level fields must match the v1 schema exactly")
    _require(payload["schema"] == SCHEMA, "schema mismatch")
    _require(payload["classification"] == CLASSIFICATION, "classification must be OWNER_LIVE_REQUIRED")

    try:
        parsed_queue_id = uuid.UUID(payload["queue_id"])
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationError("queue_id must be a canonical UUID") from exc
    _require(str(parsed_queue_id) == payload["queue_id"].lower(), "queue_id must be canonical lowercase UUID")

    repository = payload["source_repository"]
    _require(isinstance(repository, str) and REPOSITORY.fullmatch(repository) is not None, "invalid source_repository")
    _require(isinstance(payload["source_sha"], str) and HEX40.fullmatch(payload["source_sha"]) is not None, "invalid source_sha")

    target = payload["target_alias"]
    _require(isinstance(target, str) and 1 <= len(target) <= 128 and TARGET.fullmatch(target) is not None, "invalid target_alias")

    operation = payload["operation_id"]
    _require(isinstance(operation, str) and 3 <= len(operation) <= 128 and OPERATION.fullmatch(operation) is not None, "invalid operation_id")

    for key in (
        "operation_contract_digest_sha256",
        "consumer_rules_digest_sha256",
        "read_only_preflight_digest_sha256",
    ):
        value = payload[key]
        _require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"invalid {key}")

    shared_sha = payload["shared_contract_sha"]
    _require(isinstance(shared_sha, str) and HEX40.fullmatch(shared_sha) is not None, "invalid shared_contract_sha")

    baseline = payload["expected_baseline"]
    _require(isinstance(baseline, dict), "expected_baseline must be an object")
    _require(set(baseline).issubset({"kind", "value", "unavailable_reason"}), "unexpected expected_baseline field")
    _require("kind" in baseline and "value" in baseline, "expected_baseline kind/value required")
    _require(baseline["kind"] in BASELINE_KINDS, "unsupported expected_baseline kind")
    _require(isinstance(baseline["value"], str) and 1 <= len(baseline["value"]) <= 512, "invalid expected_baseline value")
    if baseline["kind"] == "UNAVAILABLE":
        reason = baseline.get("unavailable_reason")
        _require(isinstance(reason, str) and 1 <= len(reason) <= 512, "UNAVAILABLE baseline requires unavailable_reason")
    else:
        _require("unavailable_reason" not in baseline, "unavailable_reason is only valid for UNAVAILABLE baseline")

    classes = payload["allowed_mutation_classes"]
    _require(isinstance(classes, list) and 1 <= len(classes) <= 8, "allowed_mutation_classes must contain 1..8 values")
    _require(len(classes) == len(set(classes)), "allowed_mutation_classes must be unique")
    _require(all(isinstance(value, str) and MUTATION_CLASS.fullmatch(value) for value in classes), "invalid mutation class")

    maximum = payload["maximum_total_mutations"]
    _require(isinstance(maximum, int) and not isinstance(maximum, bool) and 1 <= maximum <= 16, "maximum_total_mutations must be 1..16")

    exclusions = payload["exclusions"]
    _require(isinstance(exclusions, list) and 1 <= len(exclusions) <= 32, "exclusions must contain 1..32 values")
    _require(len(exclusions) == len(set(exclusions)), "exclusions must be unique")
    _require(all(isinstance(value, str) and 1 <= len(value) <= 256 for value in exclusions), "invalid exclusion")


def final_disposition(
    *,
    queue_state: str,
    classification: str,
    exact_main_matches: bool,
    exact_main_ci_pass: bool,
    read_only_preflight_complete: bool,
    fixed_operation_proven: bool,
    ambiguity: bool = False,
) -> str:
    if queue_state != "QUEUE_SOURCE_COMPLETE":
        return "BLOCKED_SOURCE_NOT_COMPLETE"
    if ambiguity:
        return "BLOCKED_AMBIGUOUS"
    if not exact_main_matches or not exact_main_ci_pass:
        return "BLOCKED_SOURCE_EVIDENCE"
    if classification == "NO_LIVE_REQUIRED":
        return "DONE_NO_LIVE"
    if classification != "OWNER_LIVE_REQUIRED":
        return "BLOCKED_CLASSIFICATION"
    if not read_only_preflight_complete or not fixed_operation_proven:
        return "BLOCKED_LIVE_NOT_READY"
    return "OWNER_LIVE_REQUIRED"


def binding_still_current(payload: dict[str, Any], approved_binding: str, refreshed_payload: dict[str, Any]) -> bool:
    _require(HEX64.fullmatch(approved_binding) is not None, "approved binding must be a lowercase sha256")
    return binding_sha256(payload) == approved_binding == binding_sha256(refreshed_payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    validate_ready(payload)
    digest = binding_sha256(payload)
    print(f"SIMPLE_LIVE_READY=PASS")
    print(f"BINDING_SHA256={digest}")
    print(f"OWNER_COMMAND=LIVE {digest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        print(f"SIMPLE_LIVE_READY=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
