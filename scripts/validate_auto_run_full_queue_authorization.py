from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

SCHEMA = "rozkalns.auto-run-full-queue-auth.v1"
SCOPE_ALGORITHM = "CANONICAL_JSON_REPOSITORY_ISSUE_NUMBER_TITLE_BODY_V1_SHA256"
TITLE_PREFIX = "[AUTO-FULL-QUEUE][ACTIVE] "
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

PAYLOAD_FIELDS = {
    "schema",
    "queue_id",
    "repository",
    "repository_id",
    "owner_user_id",
    "shared_contract_sha",
    "activation_main_sha",
    "consumer_rules_digest_sha256",
    "scope_digest_algorithm",
    "authority",
    "issues",
}

ISSUE_FIELDS = {"number", "node_id", "scope_digest_sha256"}
AUTHORITY_FIELDS = {"source", "merge", "live"}


@dataclass(frozen=True)
class SurfaceMetadata:
    title: str
    creator_user_id: int
    configured_owner_user_id: int
    created_at: str
    updated_at: str


def _is_uuid4(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value.lower()


def canonical_scope_payload(repository: str, issue_number: int, title: str, body: str) -> bytes:
    obj = {
        "repository": repository,
        "issue_number": issue_number,
        "title": title,
        "body": body,
    }
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_scope_digest(repository: str, issue_number: int, title: str, body: str) -> str:
    return hashlib.sha256(canonical_scope_payload(repository, issue_number, title, body)).hexdigest()


def validate_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]

    if set(payload) != PAYLOAD_FIELDS:
        errors.append("payload keys mismatch")
        return errors

    if payload["schema"] != SCHEMA:
        errors.append("schema mismatch")

    if not _is_uuid4(payload["queue_id"]):
        errors.append("queue_id must be canonical UUIDv4")

    repository = payload["repository"]
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        errors.append("repository format is invalid")

    if not isinstance(payload["repository_id"], int) or isinstance(payload["repository_id"], bool) or payload["repository_id"] < 1:
        errors.append("repository_id must be a positive integer")

    if not isinstance(payload["owner_user_id"], int) or isinstance(payload["owner_user_id"], bool) or payload["owner_user_id"] < 1:
        errors.append("owner_user_id must be a positive integer")

    for field in ("shared_contract_sha", "activation_main_sha"):
        value = payload[field]
        if not isinstance(value, str) or not SHA40_RE.fullmatch(value):
            errors.append(f"{field} must be lowercase 40-hex")

    rules_digest = payload["consumer_rules_digest_sha256"]
    if not isinstance(rules_digest, str) or not SHA256_RE.fullmatch(rules_digest):
        errors.append("consumer_rules_digest_sha256 must be lowercase 64-hex")

    if payload["scope_digest_algorithm"] != SCOPE_ALGORITHM:
        errors.append("scope_digest_algorithm mismatch")

    authority = payload["authority"]
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_FIELDS:
        errors.append("authority keys mismatch")
    else:
        if authority["source"] is not True:
            errors.append("source authority must be true")
        if authority["merge"] is not True:
            errors.append("merge authority must be true")
        if authority["live"] is not False:
            errors.append("LIVE authority must be false")

    issues = payload["issues"]
    if not isinstance(issues, list):
        errors.append("issues must be an array")
        return errors
    if not 1 <= len(issues) <= 10:
        errors.append("issues length must be between 1 and 10")

    seen_numbers: set[int] = set()
    seen_node_ids: set[str] = set()
    for index, item in enumerate(issues):
        prefix = f"issues[{index}]"
        if not isinstance(item, dict) or set(item) != ISSUE_FIELDS:
            errors.append(f"{prefix} keys mismatch")
            continue

        number = item["number"]
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            errors.append(f"{prefix}.number must be a positive integer")
        elif number in seen_numbers:
            errors.append("duplicate issue number")
        else:
            seen_numbers.add(number)

        node_id = item["node_id"]
        if not isinstance(node_id, str) or not node_id or len(node_id) > 256:
            errors.append(f"{prefix}.node_id is invalid")
        elif node_id in seen_node_ids:
            errors.append("duplicate issue node_id")
        else:
            seen_node_ids.add(node_id)

        digest = item["scope_digest_sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix}.scope_digest_sha256 must be lowercase 64-hex")

    return errors


def validate_surface(metadata: SurfaceMetadata, payload: Any) -> list[str]:
    errors = validate_payload(payload)
    if errors:
        return errors

    if metadata.creator_user_id != metadata.configured_owner_user_id:
        errors.append("controller issue creator must match configured owner")
    if payload["owner_user_id"] != metadata.configured_owner_user_id:
        errors.append("payload owner_user_id must match configured owner")
    expected_title = TITLE_PREFIX + payload["queue_id"]
    if metadata.title != expected_title:
        errors.append("controller issue title must bind queue_id")
    if metadata.created_at != metadata.updated_at:
        errors.append("authorization issue body or metadata was edited after creation")
    return errors


def verify_frozen_issue(
    payload: dict[str, Any],
    *,
    issue_number: int,
    node_id: str,
    current_title: str,
    current_body: str,
) -> list[str]:
    errors: list[str] = []
    if validate_payload(payload):
        return ["authorization payload is invalid"]

    matches = [item for item in payload["issues"] if item["number"] == issue_number]
    if len(matches) != 1:
        return ["issue is not uniquely frozen in this queue"]

    frozen = matches[0]
    if frozen["node_id"] != node_id:
        errors.append("issue node identity drift")

    observed_digest = canonical_scope_digest(
        payload["repository"], issue_number, current_title, current_body
    )
    if observed_digest != frozen["scope_digest_sha256"]:
        errors.append("issue scope digest drift")
    return errors


def may_consume_item_authority(
    payload: dict[str, Any],
    *,
    active_issue: int,
    requested_issue: int,
) -> bool:
    if validate_payload(payload):
        return False
    frozen_numbers = [item["number"] for item in payload["issues"]]
    return requested_issue == active_issue and requested_issue in frozen_numbers


def merge_gate(
    payload: dict[str, Any],
    *,
    active_issue: int,
    requested_issue: int,
    expected_head_sha: str,
    observed_head_sha: str,
    exact_head_ci_pass: bool,
    reviews_pass: bool,
    scope_matches: bool,
    rules_match: bool,
) -> list[str]:
    errors: list[str] = []
    if not may_consume_item_authority(
        payload, active_issue=active_issue, requested_issue=requested_issue
    ):
        errors.append("requested issue may not consume Queue merge authority")
    if not SHA40_RE.fullmatch(expected_head_sha or ""):
        errors.append("expected_head_sha must be lowercase 40-hex")
    if expected_head_sha != observed_head_sha:
        errors.append("exact PR head drift")
    if not exact_head_ci_pass:
        errors.append("exact-head CI is not proven PASS")
    if not reviews_pass:
        errors.append("review/thread gate is not proven PASS")
    if not scope_matches:
        errors.append("frozen scope is not proven unchanged")
    if not rules_match:
        errors.append("repository rules boundary is not proven unchanged")
    return errors
