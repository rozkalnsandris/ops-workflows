#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from typing import Any, NamedTuple

RUN_SCHEMA = "rozkalns.auto-run-full-single-issue-run-state.v2"
CONTROLLER_SCHEMA = "rozkalns.auto-run-full-single-issue-controller.v2"
PHASES = {"PLANNED", "ACTIVE_SOURCE", "PR_OPEN", "WAITING_CI", "READY", "STOPPED", "DONE"}
CONTROLLER_STATES = {"IDLE", "ACTIVE", "STOPPED"}
OWNER_GATES = {None, "MERGE", "LIVE", "SCOPE_DECISION", "REAUTHORIZATION"}
RUN_FIELDS = {
    "schema", "repository", "issue_number", "run_id", "scope_digest_sha256",
    "revision", "phase", "branch", "pr_number", "correction_count",
    "stop_reason", "owner_gate", "completion",
}
CONTROLLER_FIELDS = {
    "schema", "repository", "state", "active_issue", "active_run_id",
    "active_run_digest_sha256", "last_transition_id",
}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
TRANSITION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

class ReconstructionCost(NamedTuple):
    durable_objects: int
    duplicated_mutable_fields: int

def _uuid4(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value.lower()

def active_run_digest(run: dict[str, Any]) -> str:
    payload = {
        "repository": run["repository"],
        "issue_number": run["issue_number"],
        "run_id": run["run_id"],
        "scope_digest_sha256": run["scope_digest_sha256"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()

def validate_run(run: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(run, dict):
        return ["run must be an object"]
    if set(run) != RUN_FIELDS:
        return ["run keys mismatch"]
    if run["schema"] != RUN_SCHEMA:
        errors.append("run schema mismatch")
    if not isinstance(run["repository"], str) or REPO_RE.fullmatch(run["repository"]) is None:
        errors.append("repository must be owner/name")
    if not isinstance(run["issue_number"], int) or isinstance(run["issue_number"], bool) or run["issue_number"] < 1:
        errors.append("issue_number must be positive integer")
    if not _uuid4(run["run_id"]):
        errors.append("run_id must be canonical UUIDv4")
    if not isinstance(run["scope_digest_sha256"], str) or HEX64_RE.fullmatch(run["scope_digest_sha256"]) is None:
        errors.append("scope_digest_sha256 must be lowercase 64-hex")
    if not isinstance(run["revision"], int) or isinstance(run["revision"], bool) or run["revision"] < 0:
        errors.append("revision must be non-negative integer")
    if run["phase"] not in PHASES:
        errors.append("invalid phase")
    if run["branch"] is not None and (not isinstance(run["branch"], str) or not run["branch"]):
        errors.append("branch must be non-empty string or null")
    if run["pr_number"] is not None and (
        not isinstance(run["pr_number"], int) or isinstance(run["pr_number"], bool) or run["pr_number"] < 1
    ):
        errors.append("pr_number must be positive integer or null")
    if run["pr_number"] is not None and run["branch"] is None:
        errors.append("pr_number requires branch")
    if not isinstance(run["correction_count"], int) or isinstance(run["correction_count"], bool) or not 0 <= run["correction_count"] <= 2:
        errors.append("correction_count must be 0..2")
    if run["stop_reason"] is not None and (not isinstance(run["stop_reason"], str) or not run["stop_reason"]):
        errors.append("stop_reason must be non-empty string or null")
    if run["owner_gate"] not in OWNER_GATES:
        errors.append("invalid owner_gate")
    completion = run["completion"]
    if completion is not None:
        if not isinstance(completion, dict) or set(completion) != {"exact_main_sha", "receipt_ref"}:
            errors.append("completion keys mismatch")
        else:
            if not isinstance(completion["exact_main_sha"], str) or SHA40_RE.fullmatch(completion["exact_main_sha"]) is None:
                errors.append("completion.exact_main_sha must be lowercase 40-hex")
            if completion["receipt_ref"] is not None and (
                not isinstance(completion["receipt_ref"], str) or not completion["receipt_ref"]
            ):
                errors.append("completion.receipt_ref must be non-empty string or null")
    if run["phase"] == "STOPPED":
        if run["stop_reason"] is None:
            errors.append("STOPPED requires stop_reason")
        if completion is not None:
            errors.append("STOPPED cannot have completion")
    elif run["stop_reason"] is not None:
        errors.append("stop_reason must be null unless STOPPED")
    if run["phase"] == "DONE":
        if completion is None:
            errors.append("DONE requires completion")
        if run["owner_gate"] is not None:
            errors.append("DONE owner_gate must be null")
    elif completion is not None:
        errors.append("completion must be null unless DONE")
    if run["phase"] in {"WAITING_CI", "READY"} and run["pr_number"] is None:
        errors.append(f"{run['phase']} requires pr_number")
    return errors

def validate_controller(controller: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(controller, dict):
        return ["controller must be an object"]
    if set(controller) != CONTROLLER_FIELDS:
        return ["controller keys mismatch"]
    if controller["schema"] != CONTROLLER_SCHEMA:
        errors.append("controller schema mismatch")
    if not isinstance(controller["repository"], str) or REPO_RE.fullmatch(controller["repository"]) is None:
        errors.append("controller repository must be owner/name")
    if controller["state"] not in CONTROLLER_STATES:
        errors.append("invalid controller state")
    issue = controller["active_issue"]
    run_id = controller["active_run_id"]
    digest = controller["active_run_digest_sha256"]
    tid = controller["last_transition_id"]
    if issue is not None and (not isinstance(issue, int) or isinstance(issue, bool) or issue < 1):
        errors.append("active_issue must be positive integer or null")
    if run_id is not None and not _uuid4(run_id):
        errors.append("active_run_id must be UUIDv4 or null")
    if digest is not None and (not isinstance(digest, str) or HEX64_RE.fullmatch(digest) is None):
        errors.append("active_run_digest_sha256 must be lowercase 64-hex or null")
    if tid is not None and (not isinstance(tid, str) or TRANSITION_RE.fullmatch(tid) is None):
        errors.append("last_transition_id invalid")
    if controller["state"] == "IDLE":
        if any(value is not None for value in (issue, run_id, digest)):
            errors.append("IDLE active binding must be null")
    else:
        if issue is None or run_id is None or digest is None:
            errors.append(f"{controller['state']} requires full active binding")
    return errors

def make_planned(repository: str, issue_number: int, run_id: str, scope_digest_sha256: str) -> dict[str, Any]:
    run = {
        "schema": RUN_SCHEMA,
        "repository": repository,
        "issue_number": issue_number,
        "run_id": run_id,
        "scope_digest_sha256": scope_digest_sha256,
        "revision": 0,
        "phase": "PLANNED",
        "branch": None,
        "pr_number": None,
        "correction_count": 0,
        "stop_reason": None,
        "owner_gate": None,
        "completion": None,
    }
    errors = validate_run(run)
    if errors:
        raise ValueError("; ".join(errors))
    return run

def make_idle_controller(repository: str, last_transition_id: str | None = None) -> dict[str, Any]:
    controller = {
        "schema": CONTROLLER_SCHEMA,
        "repository": repository,
        "state": "IDLE",
        "active_issue": None,
        "active_run_id": None,
        "active_run_digest_sha256": None,
        "last_transition_id": last_transition_id,
    }
    errors = validate_controller(controller)
    if errors:
        raise ValueError("; ".join(errors))
    return controller

def _validate_binding(run: dict[str, Any], controller: dict[str, Any]) -> None:
    run_errors = validate_run(run)
    ctl_errors = validate_controller(controller)
    if run_errors or ctl_errors:
        raise ValueError("; ".join(run_errors + ctl_errors))
    if controller["repository"] != run["repository"]:
        raise ValueError("controller repository mismatch")
    if controller["state"] not in {"ACTIVE", "STOPPED"}:
        raise ValueError("controller must hold active binding")
    if controller["active_issue"] != run["issue_number"] or controller["active_run_id"] != run["run_id"]:
        raise ValueError("controller target/run mismatch")
    if controller["active_run_digest_sha256"] != active_run_digest(run):
        raise ValueError("controller active run digest mismatch")

def activate_controller(controller: dict[str, Any], run: dict[str, Any], transition_id: str) -> dict[str, Any]:
    if validate_controller(controller):
        raise ValueError("; ".join(validate_controller(controller)))
    if validate_run(run):
        raise ValueError("; ".join(validate_run(run)))
    if run["phase"] != "PLANNED":
        raise ValueError("controller activation requires PLANNED run")
    if not TRANSITION_RE.fullmatch(transition_id):
        raise ValueError("transition_id invalid")
    intended_digest = active_run_digest(run)
    if controller["state"] == "ACTIVE":
        if (
            controller["active_issue"] == run["issue_number"]
            and controller["active_run_id"] == run["run_id"]
            and controller["active_run_digest_sha256"] == intended_digest
            and controller["last_transition_id"] == transition_id
        ):
            return copy.deepcopy(controller)
        raise ValueError("controller already ACTIVE for another or conflicting run")
    if controller["state"] == "STOPPED":
        raise ValueError("STOPPED controller requires explicit release before new activation")
    result = copy.deepcopy(controller)
    result.update({
        "state": "ACTIVE",
        "active_issue": run["issue_number"],
        "active_run_id": run["run_id"],
        "active_run_digest_sha256": intended_digest,
        "last_transition_id": transition_id,
    })
    if validate_controller(result):
        raise ValueError("; ".join(validate_controller(result)))
    return result

_ALLOWED = {
    "PLANNED": {"ACTIVE_SOURCE"},
    "ACTIVE_SOURCE": {"PR_OPEN"},
    "PR_OPEN": {"WAITING_CI"},
    "WAITING_CI": {"WAITING_CI", "READY"},
    "READY": {"DONE"},
}

def transition_run(
    run: dict[str, Any],
    controller: dict[str, Any],
    *,
    expected_revision: int,
    transition_id: str,
    next_phase: str,
    branch: str | None = None,
    pr_number: int | None = None,
    correction_count: int | None = None,
    owner_gate: str | None = None,
    stop_reason: str | None = None,
    completion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_binding(run, controller)
    if controller["state"] != "ACTIVE":
        raise ValueError("run transition requires ACTIVE controller")
    if not TRANSITION_RE.fullmatch(transition_id):
        raise ValueError("transition_id invalid")
    if controller["last_transition_id"] == transition_id:
        if run["revision"] != expected_revision + 1:
            raise ValueError("transition id collision with unexpected revision")
        checks = {
            "phase": next_phase,
            "branch": branch if branch is not None else run["branch"],
            "pr_number": pr_number if pr_number is not None else run["pr_number"],
            "correction_count": correction_count if correction_count is not None else run["correction_count"],
            "owner_gate": owner_gate,
            "stop_reason": stop_reason if next_phase == "STOPPED" else None,
            "completion": completion if next_phase == "DONE" else None,
        }
        if any(run[key] != value for key, value in checks.items()):
            raise ValueError("transition id content collision")
        return copy.deepcopy(run)
    if run["revision"] != expected_revision:
        raise ValueError("stale revision")
    if run["phase"] in {"STOPPED", "DONE"}:
        raise ValueError(f"{run['phase']} is terminal for this run")
    if next_phase == "STOPPED":
        if not stop_reason:
            raise ValueError("STOPPED transition requires stop_reason")
    elif next_phase not in _ALLOWED.get(run["phase"], set()):
        raise ValueError(f"invalid phase transition {run['phase']}->{next_phase}")
    result = copy.deepcopy(run)
    result["revision"] += 1
    result["phase"] = next_phase
    if branch is not None:
        result["branch"] = branch
    if pr_number is not None:
        result["pr_number"] = pr_number
    if correction_count is not None:
        if next_phase != "WAITING_CI":
            raise ValueError("correction_count update only allowed in WAITING_CI transition")
        if correction_count != run["correction_count"] + 1:
            raise ValueError("correction_count must increment exactly one")
        result["correction_count"] = correction_count
    elif run["phase"] == "WAITING_CI" and next_phase == "WAITING_CI":
        raise ValueError("WAITING_CI self-transition requires correction_count increment")
    result["owner_gate"] = owner_gate
    result["stop_reason"] = stop_reason if next_phase == "STOPPED" else None
    result["completion"] = completion if next_phase == "DONE" else None
    errors = validate_run(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result

def apply_transition_to_controller(
    controller: dict[str, Any],
    run_after: dict[str, Any],
    transition_id: str,
) -> dict[str, Any]:
    _validate_binding(run_after, controller)
    if controller["state"] != "ACTIVE":
        raise ValueError("controller transition requires ACTIVE controller")
    if not TRANSITION_RE.fullmatch(transition_id):
        raise ValueError("transition_id invalid")
    if controller["last_transition_id"] == transition_id:
        return copy.deepcopy(controller)
    result = copy.deepcopy(controller)
    result["last_transition_id"] = transition_id
    if run_after["phase"] == "STOPPED":
        result["state"] = "STOPPED"
    errors = validate_controller(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result

def release_completed(controller: dict[str, Any], run: dict[str, Any], transition_id: str) -> dict[str, Any]:
    _validate_binding(run, controller)
    if run["phase"] != "DONE":
        raise ValueError("completed release requires DONE run")
    if controller["state"] != "ACTIVE":
        raise ValueError("completed release requires ACTIVE controller")
    return make_idle_controller(run["repository"], transition_id)

def release_aborted(
    controller: dict[str, Any],
    run: dict[str, Any],
    transition_id: str,
    *,
    explicit_abort_authorized: bool,
) -> dict[str, Any]:
    _validate_binding(run, controller)
    if run["phase"] != "STOPPED" or controller["state"] != "STOPPED":
        raise ValueError("aborted release requires STOPPED run/controller")
    if not explicit_abort_authorized:
        raise ValueError("explicit abort/release decision required")
    return make_idle_controller(run["repository"], transition_id)

def reconstruct_normalized(run: dict[str, Any], controller: dict[str, Any]) -> dict[str, Any]:
    run_errors = validate_run(run)
    ctl_errors = validate_controller(controller)
    if run_errors or ctl_errors:
        raise ValueError("; ".join(run_errors + ctl_errors))
    if controller["state"] == "IDLE":
        if run["phase"] not in {"DONE", "STOPPED", "PLANNED"}:
            raise ValueError("nonterminal active phase cannot reconstruct with IDLE controller")
    else:
        _validate_binding(run, controller)
        if controller["state"] == "STOPPED" and run["phase"] != "STOPPED":
            raise ValueError("STOPPED controller requires STOPPED run")
    return {
        "repository": run["repository"],
        "issue_number": run["issue_number"],
        "run_id": run["run_id"],
        "phase": run["phase"],
        "revision": run["revision"],
        "branch": run["branch"],
        "pr_number": run["pr_number"],
        "correction_count": run["correction_count"],
        "stop_reason": run["stop_reason"],
        "owner_gate": run["owner_gate"],
        "completion": copy.deepcopy(run["completion"]),
    }

def reconstruct_legacy(
    *,
    target: dict[str, Any],
    controller: dict[str, Any],
    activation_receipt: dict[str, Any],
    status_receipt: dict[str, Any],
) -> dict[str, Any]:
    required_target = {"repository", "issue_number", "scope_digest_sha256"}
    required_controller = {"repository", "issue_number", "run_id", "phase", "branch", "pr_number", "correction_count"}
    required_activation = {"repository", "issue_number", "run_id"}
    required_status = {"repository", "issue_number", "run_id", "phase", "pr_number", "stop_reason", "owner_gate", "completion"}
    for name, obj, fields in (
        ("target", target, required_target),
        ("controller", controller, required_controller),
        ("activation_receipt", activation_receipt, required_activation),
        ("status_receipt", status_receipt, required_status),
    ):
        if not isinstance(obj, dict) or set(obj) != fields:
            raise ValueError(f"legacy {name} keys mismatch")
    repo_values = {target["repository"], controller["repository"], activation_receipt["repository"], status_receipt["repository"]}
    issue_values = {target["issue_number"], controller["issue_number"], activation_receipt["issue_number"], status_receipt["issue_number"]}
    run_values = {controller["run_id"], activation_receipt["run_id"], status_receipt["run_id"]}
    phase_values = {controller["phase"], status_receipt["phase"]}
    pr_values = {controller["pr_number"], status_receipt["pr_number"]}
    if len(repo_values) != 1 or len(issue_values) != 1 or len(run_values) != 1 or len(phase_values) != 1 or len(pr_values) != 1:
        raise ValueError("legacy duplicated state collision")
    return {
        "repository": target["repository"],
        "issue_number": target["issue_number"],
        "run_id": controller["run_id"],
        "scope_digest_sha256": target["scope_digest_sha256"],
        "phase": controller["phase"],
        "branch": controller["branch"],
        "pr_number": controller["pr_number"],
        "correction_count": controller["correction_count"],
        "stop_reason": status_receipt["stop_reason"],
        "owner_gate": status_receipt["owner_gate"],
        "completion": copy.deepcopy(status_receipt["completion"]),
    }

def normalized_reconstruction_cost() -> ReconstructionCost:
    return ReconstructionCost(durable_objects=2, duplicated_mutable_fields=0)

def legacy_reconstruction_cost() -> ReconstructionCost:
    return ReconstructionCost(durable_objects=4, duplicated_mutable_fields=7)
