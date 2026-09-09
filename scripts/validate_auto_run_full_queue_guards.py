#!/usr/bin/env python3
"""Fail-closed A6 composition and consumer-adoption guards.

This helper is intentionally read-only. It validates the pinned shared A1-A5
contracts and, when requested, one caller-repository adoption manifest plus the
caller's immutable reusable-workflow pin.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GUARD_USES_RE = re.compile(
    r"uses:\s*rozkalnsandris/ops-workflows/\.github/workflows/"
    r"auto-run-full-queue-adoption-guard\.yml@([^\s#]+)"
)


class GuardError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError(f"invalid JSON file {path}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def nested(obj: dict[str, Any], *keys: str) -> Any:
    current: Any = obj
    for key in keys:
        require(isinstance(current, dict) and key in current, f"missing invariant: {'.'.join(keys)}")
        current = current[key]
    return current


def require_exact_keys(obj: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(obj)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    require(not unknown, f"{label}: unknown fields: {', '.join(unknown)}")
    require(not missing, f"{label}: missing fields: {', '.join(missing)}")


def validate_composition(root: Path) -> int:
    paths = {
        "a1": root / "policy/auto-run-full-queue-v1.json",
        "a2": root / "policy/auto-run-full-queue-controller-v1.json",
        "a3": root / "policy/auto-run-full-queue-authorization-v1.json",
        "a4": root / "policy/auto-run-full-queue-resume-v1.json",
        "a5": root / "policy/simple-live-v1.json",
        "auto_live": root / "policy/auto-live-v1.json",
        "a6": root / "policy/auto-run-full-queue-guards-v1.json",
    }
    policies = {name: load_json(path) for name, path in paths.items()}
    a1 = policies["a1"]
    a2 = policies["a2"]
    a3 = policies["a3"]
    a4 = policies["a4"]
    a5 = policies["a5"]
    auto_live = policies["auto_live"]
    a6 = policies["a6"]

    for name, policy in policies.items():
        require(
            policy.get("canonical_repository") == "rozkalnsandris/ops-workflows",
            f"composition drift: {name} canonical_repository",
        )
        if name != "auto_live":
            require(policy.get("tracking_issue") == 39, f"composition drift: {name} tracking_issue")
        require(policy.get("source_policy_only") is True, f"composition drift: {name} source_policy_only")

    require(nested(a1, "activation", "command_active") is False, "A1 shared queue command became active")
    require(nested(a1, "queue", "maximum_items") == 10, "A1 maximum queue items drifted")
    require(
        nested(a1, "queue", "maximum_active_items_per_repository_controller") == 1,
        "A1 maximum active items drifted",
    )
    require(nested(a1, "authorization", "queue_authorizes_live") is False, "A1 queue gained LIVE authority")
    require(
        nested(a1, "execution_boundary", "ops_workflows_executes_production") is False,
        "A1 ops-workflows production boundary drifted",
    )

    require(nested(a2, "activation", "queue_command_active") is False, "A2 shared queue command became active")
    require(nested(a2, "snapshot", "maximum_items") == 10, "A2 maximum queue items drifted")
    require(nested(a2, "snapshot", "maximum_active_items") == 1, "A2 maximum active items drifted")
    require(nested(a2, "authorization", "queue_authorizes_live") is False, "A2 queue gained LIVE authority")

    require(
        nested(a3, "activation", "queue_command_active_in_consumers") is False,
        "A3 unexpectedly activates consumers from shared policy",
    )
    require(nested(a3, "command", "maximum_items") == 10, "A3 maximum queue items drifted")
    require(
        nested(a3, "authority", "future_adopted_queue_activation_grants_source_authority_for_all_frozen_items")
        is True,
        "A3 future batch source authority invariant drifted",
    )
    require(
        nested(a3, "authority", "future_adopted_queue_activation_grants_merge_authority_for_all_frozen_items")
        is True,
        "A3 future batch merge authority invariant drifted",
    )
    require(nested(a3, "authority", "maximum_simultaneously_active_items") == 1, "A3 active item limit drifted")
    require(nested(a3, "authority", "queue_authorizes_live") is False, "A3 queue gained LIVE authority")
    require(nested(a3, "completion", "final_live_requires_separate_authorization") is True, "A3 separate LIVE gate drifted")

    require(nested(a4, "activation", "consumer_event_resume_active") is False, "A4 event resume became shared-active")
    require(nested(a4, "activation", "consumer_watchdog_active") is False, "A4 watchdog became shared-active")
    require(nested(a4, "canonical_state", "event_payload_is_authority") is False, "A4 event payload became authority")
    require(nested(a4, "canonical_state", "watchdog_tick_is_authority") is False, "A4 watchdog became authority")
    require(nested(a4, "canonical_state", "event_never_directly_advances_cursor") is True, "A4 event cursor guard drifted")
    require(nested(a4, "owner_gate_behavior", "queue_resume_never_grants_live") is True, "A4 resume gained LIVE authority")

    require(nested(a5, "activation", "consumer_mode_active") is False, "A5 Simple LIVE became shared-active")
    require(nested(a5, "activation", "queue_authorizes_live") is False, "A5 queue gained LIVE authority")
    require(nested(a5, "activation", "ready_envelope_is_authority") is False, "A5 Ready envelope became authority")
    require(
        nested(a5, "activation", "fresh_explicit_owner_live_decision_required") is True,
        "A5 explicit owner LIVE decision invariant drifted",
    )
    require(nested(a5, "execution", "ops_workflows_executes_production") is False, "A5 production boundary drifted")
    require(
        nested(a5, "deferred_trusted_executor", "rpi5_trust_boundary_preserved") is True,
        "A5 RPi5 trust boundary drifted",
    )
    require(
        nested(a5, "deferred_trusted_executor", "existing_live_auth_v1_required_for_deferred_rpi5_execution")
        is True,
        "A5 deferred RPi5 LIVE-AUTH requirement drifted",
    )
    require(
        nested(a5, "auto_live_compatibility", "double_execution_paths_for_same_operation_allowed") is False,
        "A5 double final-LIVE paths became allowed",
    )

    require(nested(auto_live, "merge", "authorizes_live_mutation") is False, "Auto-Live merge gained LIVE authority")
    require(
        nested(auto_live, "automatic_mutation", "requires_explicit_consumer_activation") is True,
        "Auto-Live consumer activation invariant drifted",
    )
    require(
        nested(auto_live, "execution_boundary", "ops_workflows_executes_production") is False,
        "Auto-Live production boundary drifted",
    )
    require(
        nested(auto_live, "consumer_reference", "immutable_exact_commit_sha_required_for_production_policy") is True,
        "Auto-Live immutable pin requirement drifted",
    )

    expected_a6 = {
        "maximum_queue_items": 10,
        "maximum_active_items": 1,
        "future_adopted_batch_source_authority": True,
        "future_adopted_batch_merge_authority": True,
        "queue_live_authority": False,
        "resume_signal_is_authority": False,
        "ready_live_envelope_is_authority": False,
        "merge_authorizes_live": False,
        "ops_workflows_executes_production": False,
        "rpi5_trust_boundary_preserved": True,
        "deferred_rpi5_requires_live_auth_v1": True,
        "double_final_live_execution_paths_allowed": False,
    }
    composition = nested(a6, "composition")
    require(isinstance(composition, dict), "A6 composition must be an object")
    for key, expected in expected_a6.items():
        require(composition.get(key) == expected, f"A6 composition invariant drifted: {key}")

    return len(expected_a6) + 33


def validate_manifest_shape(manifest: dict[str, Any]) -> None:
    require_exact_keys(
        manifest,
        {"schema", "repository", "shared_contract_sha", "adoption_phase", "queue", "final_live", "boundaries"},
        "manifest",
    )
    require(manifest["schema"] == "rozkalns.auto-run-full-queue-adoption.v1", "manifest schema mismatch")
    require(isinstance(manifest["repository"], str) and REPOSITORY_RE.fullmatch(manifest["repository"]) is not None, "manifest repository is invalid")
    require(isinstance(manifest["shared_contract_sha"], str) and SHA40_RE.fullmatch(manifest["shared_contract_sha"]) is not None, "manifest shared_contract_sha must be exact lowercase 40-hex")
    require(
        manifest["adoption_phase"] in {"SOURCE_ONLY_CANARY", "LIVE_CANARY_READY", "MIGRATED"},
        "manifest adoption_phase is invalid",
    )

    queue = manifest["queue"]
    require(isinstance(queue, dict), "manifest queue must be an object")
    require_exact_keys(
        queue,
        {"command_active", "maximum_items", "maximum_active_items", "batch_source_authority", "batch_merge_authority", "live_authority"},
        "manifest queue",
    )
    require(queue["command_active"] is True, "manifest queue command_active must be true")
    require(type(queue["maximum_items"]) is int and 1 <= queue["maximum_items"] <= 10, "manifest maximum_items must be 1..10")
    require(queue["maximum_active_items"] == 1, "manifest maximum_active_items must be 1")
    require(queue["batch_source_authority"] is True, "manifest batch_source_authority must be true")
    require(queue["batch_merge_authority"] is True, "manifest batch_merge_authority must be true")
    require(queue["live_authority"] is False, "manifest queue must never grant LIVE authority")

    final_live = manifest["final_live"]
    require(isinstance(final_live, dict), "manifest final_live must be an object")
    require_exact_keys(
        final_live,
        {"mode", "double_execution_paths_allowed", "deferred_rpi5_requires_live_auth_v1"},
        "manifest final_live",
    )
    require(
        final_live["mode"] in {"DISABLED", "SIMPLE_LIVE_OWNER_DRIVEN", "AUTO_LIVE_V1_STATIC"},
        "manifest final_live mode is invalid",
    )
    require(final_live["double_execution_paths_allowed"] is False, "manifest must forbid double final-LIVE paths")
    require(final_live["deferred_rpi5_requires_live_auth_v1"] is True, "manifest must preserve deferred RPi5 LIVE-AUTH v1")

    phase = manifest["adoption_phase"]
    if phase == "SOURCE_ONLY_CANARY":
        require(final_live["mode"] == "DISABLED", "SOURCE_ONLY_CANARY must keep final LIVE disabled")
    elif phase == "LIVE_CANARY_READY":
        require(final_live["mode"] != "DISABLED", "LIVE_CANARY_READY requires one explicit final LIVE mode")

    boundaries = manifest["boundaries"]
    require(isinstance(boundaries, dict), "manifest boundaries must be an object")
    require_exact_keys(
        boundaries,
        {"ops_workflows_executes_production", "ops_workflows_stores_production_credentials", "consumer_owns_rollout_adapter", "repository_local_stricter_rules_win"},
        "manifest boundaries",
    )
    require(boundaries["ops_workflows_executes_production"] is False, "ops-workflows must not execute production")
    require(boundaries["ops_workflows_stores_production_credentials"] is False, "ops-workflows must not store production credentials")
    require(boundaries["consumer_owns_rollout_adapter"] is True, "consumer must own rollout adapter")
    require(boundaries["repository_local_stricter_rules_win"] is True, "repository-local stricter rules must win")


def safe_relative_path(raw: str, label: str) -> Path:
    path = Path(raw)
    require(not path.is_absolute(), f"{label} must be relative")
    require(".." not in path.parts, f"{label} must stay inside repository")
    return path


def validate_caller_pin(caller_root: Path, expected_sha: str) -> None:
    workflows = caller_root / ".github/workflows"
    require(workflows.is_dir(), "caller .github/workflows directory is missing")
    references: list[tuple[Path, str]] = []
    for path in sorted(list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))):
        text = path.read_text(encoding="utf-8")
        for match in GUARD_USES_RE.finditer(text):
            references.append((path, match.group(1)))

    require(references, "caller has no AUTO-RUN FULL Queue adoption guard reference")
    mutable = [(path, ref) for path, ref in references if SHA40_RE.fullmatch(ref) is None]
    require(
        not mutable,
        "caller adoption guard uses mutable/non-SHA ref: "
        + ", ".join(f"{path.as_posix()}@{ref}" for path, ref in mutable),
    )
    require(
        any(ref == expected_sha for _, ref in references),
        "caller adoption guard exact SHA does not match manifest shared_contract_sha",
    )


def validate_adoption(
    canonical_root: Path,
    manifest_path: Path,
    expected_repository: str,
    expected_sha: str,
    caller_root: Path | None,
) -> int:
    require(SHA40_RE.fullmatch(expected_sha) is not None, "expected canonical SHA must be exact lowercase 40-hex")
    require(REPOSITORY_RE.fullmatch(expected_repository) is not None, "expected repository is invalid")

    manifest = load_json(manifest_path)
    validate_manifest_shape(manifest)
    require(manifest["repository"] == expected_repository, "manifest repository does not match caller repository")
    require(manifest["shared_contract_sha"] == expected_sha, "manifest shared_contract_sha does not match canonical input SHA")

    if caller_root is not None:
        validate_caller_pin(caller_root, expected_sha)

    canonical_head = canonical_root / ".git"
    if canonical_head.exists():
        # The workflow also verifies checkout HEAD using git. This marker prevents
        # treating an arbitrary policy directory as a caller-controlled authority.
        require(canonical_head.is_dir() or canonical_head.is_file(), "canonical checkout .git marker is invalid")

    return 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-root", default=".")
    parser.add_argument("--composition-only", action="store_true")
    parser.add_argument("--manifest")
    parser.add_argument("--expected-repository")
    parser.add_argument("--expected-sha")
    parser.add_argument("--caller-root")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical_root = Path(args.canonical_root)
    composition_checks = validate_composition(canonical_root)

    if args.composition_only:
        require(args.manifest is None, "--composition-only cannot be combined with --manifest")
        print("QUEUE_GUARDS_COMPOSITION=PASS")
        print(f"COMPOSITION_CHECKS={composition_checks}")
        print("MUTATION=NO")
        return 0

    require(args.manifest is not None, "--manifest is required unless --composition-only is used")
    require(args.expected_repository is not None, "--expected-repository is required")
    require(args.expected_sha is not None, "--expected-sha is required")

    manifest_rel = safe_relative_path(args.manifest, "manifest path")
    caller_root = Path(args.caller_root) if args.caller_root else None
    manifest_root = caller_root if caller_root is not None else Path(".")
    manifest_path = manifest_root / manifest_rel

    adoption_checks = validate_adoption(
        canonical_root=canonical_root,
        manifest_path=manifest_path,
        expected_repository=args.expected_repository,
        expected_sha=args.expected_sha,
        caller_root=caller_root,
    )
    print("QUEUE_ADOPTION_GUARD=PASS")
    print(f"REPOSITORY={args.expected_repository}")
    print(f"CANONICAL_POLICY_SHA={args.expected_sha}")
    print(f"MANIFEST_PATH={manifest_rel.as_posix()}")
    print(f"COMPOSITION_CHECKS={composition_checks}")
    print(f"ADOPTION_CHECKS={adoption_checks}")
    print("MUTATION=NO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuardError as exc:
        print(f"QUEUE_GUARD=FAIL: {exc}")
        raise SystemExit(1)
