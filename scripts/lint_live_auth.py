from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

AUTHORIZATION_REPOSITORY = "rozkalnsandris/ops-workflows"
AUTHORIZATION_REPOSITORY_ID = 1328835922
OWNER_USER_ID = 277435981
LIVE_AUTH_SCHEMA = "rozkalns.live-auth.v1"
TTL_SECONDS = 600
MAX_FUTURE_SKEW_SECONDS = 30
MAX_BODY_BYTES = 16 * 1024

START_MARKER = "<!-- rozkalns-live-auth:v1 -->"
END_MARKER = "<!-- /rozkalns-live-auth:v1 -->"
PAYLOAD_RE = re.compile(
    re.escape(START_MARKER)
    + r"\n```json\n(?P<payload>.*?)\n```\n"
    + re.escape(END_MARKER),
    re.DOTALL,
)
TITLE_RE = re.compile(r"^\[LIVE-AUTH\]\[PENDING\] (?P<target>[a-z0-9][a-z0-9._-]{0,63})$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
ROLLBACK_POLICIES = frozenset({"NONE", "BUILTIN_TRANSACTIONAL_V1"})

PAYLOAD_FIELDS = frozenset(
    {
        "schema", "request_id", "queue_repository", "queue_issue", "source_repository",
        "source_sha", "target_alias", "operation_id", "expected_baseline", "mutation_budget",
        "rollback_policy", "exclusions", "dependencies",
    }
)
BASELINE_FIELDS = frozenset({"kind", "value"})
BUDGET_FIELDS = frozenset({"category", "max_operations"})


class LiveAuthLintError(ValueError):
    pass


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LiveAuthLintError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise LiveAuthLintError(f"non-finite JSON number is forbidden: {value}")


def _parse_json_strict(raw: str) -> Mapping[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except LiveAuthLintError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LiveAuthLintError("malformed JSON payload") from exc
    if type(value) is not dict:
        raise LiveAuthLintError("payload root must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], where: str) -> None:
    actual = frozenset(value.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise LiveAuthLintError(f"{where} keys mismatch; missing={missing}, extra={extra}")


def _string(value: Any, where: str, max_len: int, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise LiveAuthLintError(f"{where} must be a non-empty string of at most {max_len} characters")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise LiveAuthLintError(f"{where} contains invalid Unicode") from exc
    if pattern is not None and pattern.fullmatch(value) is None:
        raise LiveAuthLintError(f"{where} format is invalid")
    return value


def _positive_int(value: Any, where: str, maximum: int) -> int:
    if type(value) is not int or value < 1 or value > maximum:
        raise LiveAuthLintError(f"{where} must be an integer in range 1..{maximum}")
    return value


def _uuid4(value: Any) -> str:
    text = _string(value, "request_id", 36)
    try:
        parsed = uuid.UUID(text)
    except ValueError as exc:
        raise LiveAuthLintError("request_id must be canonical lowercase UUIDv4") from exc
    if parsed.version != 4 or str(parsed) != text:
        raise LiveAuthLintError("request_id must be canonical lowercase UUIDv4")
    return text


def _string_list(value: Any, where: str) -> list[str]:
    if type(value) is not list or len(value) > 32:
        raise LiveAuthLintError(f"{where} must be a list with at most 32 entries")
    return [_string(item, f"{where}[{index}]", 256) for index, item in enumerate(value)]


def _validate_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    _exact_keys(payload, PAYLOAD_FIELDS, "payload")
    if payload["schema"] != LIVE_AUTH_SCHEMA:
        raise LiveAuthLintError(f"schema must be {LIVE_AUTH_SCHEMA}")
    _uuid4(payload["request_id"])
    queue_repository = _string(payload["queue_repository"], "queue_repository", 201, REPOSITORY_RE)
    if queue_repository != AUTHORIZATION_REPOSITORY:
        raise LiveAuthLintError(f"queue_repository must be {AUTHORIZATION_REPOSITORY}")
    _positive_int(payload["queue_issue"], "queue_issue", 2_147_483_647)
    _string(payload["source_repository"], "source_repository", 201, REPOSITORY_RE)
    _string(payload["source_sha"], "source_sha", 40, SHA_RE)
    _string(payload["target_alias"], "target_alias", 64, IDENTIFIER_RE)
    _string(payload["operation_id"], "operation_id", 128, IDENTIFIER_RE)

    baseline = payload["expected_baseline"]
    if type(baseline) is not dict:
        raise LiveAuthLintError("expected_baseline must be an object")
    _exact_keys(baseline, BASELINE_FIELDS, "expected_baseline")
    _string(baseline["kind"], "expected_baseline.kind", 64, IDENTIFIER_RE)
    _string(baseline["value"], "expected_baseline.value", 512)

    budget = payload["mutation_budget"]
    if type(budget) is not list or not 1 <= len(budget) <= 16:
        raise LiveAuthLintError("mutation_budget must contain 1..16 entries")
    seen: set[str] = set()
    for index, item in enumerate(budget):
        if type(item) is not dict:
            raise LiveAuthLintError(f"mutation_budget[{index}] must be an object")
        _exact_keys(item, BUDGET_FIELDS, f"mutation_budget[{index}]")
        category = _string(item["category"], f"mutation_budget[{index}].category", 128, IDENTIFIER_RE)
        if category in seen:
            raise LiveAuthLintError(f"duplicate mutation category: {category}")
        seen.add(category)
        _positive_int(item["max_operations"], f"mutation_budget[{index}].max_operations", 100)

    rollback = _string(payload["rollback_policy"], "rollback_policy", 64)
    if rollback not in ROLLBACK_POLICIES:
        raise LiveAuthLintError(f"unsupported rollback_policy: {rollback}")
    _string_list(payload["exclusions"], "exclusions")
    _string_list(payload["dependencies"], "dependencies")
    return payload


def lint(title: str, body: str, *, actor_id: int | None = None, actor_type: str | None = None) -> list[str]:
    errors: list[str] = []
    title_match = TITLE_RE.fullmatch(title or "")
    if title_match is None:
        return ["title must match [LIVE-AUTH][PENDING] <target_alias>"]
    try:
        encoded = body.encode("utf-8", "strict")
    except UnicodeEncodeError:
        return ["issue body contains invalid Unicode"]
    if not body or len(encoded) > MAX_BODY_BYTES:
        return [f"issue body must contain 1..{MAX_BODY_BYTES} UTF-8 bytes"]
    if body.count(START_MARKER) != 1 or body.count(END_MARKER) != 1:
        return ["exactly one LIVE-AUTH authority block is required"]
    match = PAYLOAD_RE.search(body)
    if match is None:
        return ["LIVE-AUTH markers/fence are malformed"]
    try:
        payload = _validate_payload(_parse_json_strict(match.group("payload")))
    except LiveAuthLintError as exc:
        errors.append(str(exc))
        return errors
    if payload["target_alias"] != title_match.group("target"):
        errors.append("title target alias must equal payload target_alias")
    if actor_id is not None and actor_id != OWNER_USER_ID:
        errors.append(f"issue author id must be configured owner id {OWNER_USER_ID}")
    if actor_type is not None and actor_type != "User":
        errors.append("issue author type must be User")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--actor-id", type=int)
    parser.add_argument("--actor-type")
    args = parser.parse_args()
    body = Path(args.body_file).read_text(encoding="utf-8")
    errors = lint(args.title, body, actor_id=args.actor_id, actor_type=args.actor_type)
    if errors:
        print("LIVE_AUTH_LINT=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("LIVE_AUTH_LINT=PASS")
    print("AUTHORITY_DECISION=NO")
    print("MUTATION=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
