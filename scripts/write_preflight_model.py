from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

ELIGIBLE = "WRITE_PREFLIGHT_ELIGIBLE"
ALREADY_SATISFIED = "WRITE_PREFLIGHT_ALREADY_SATISFIED"
CONFLICT = "WRITE_PREFLIGHT_CONFLICT"
INVALID_HEAD_BASE = "WRITE_PREFLIGHT_INVALID_HEAD_BASE"
DUPLICATE_EXACT = "WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED"
DUPLICATE_CONFLICT = "WRITE_PREFLIGHT_DUPLICATE_CONFLICT"
AUTHORITY_DRIFT = "WRITE_PREFLIGHT_AUTHORITY_DRIFT"
CAPABILITY_UNAVAILABLE = "WRITE_PREFLIGHT_CAPABILITY_UNAVAILABLE"


@dataclass(frozen=True)
class PreflightResult:
    disposition: str
    dispatch_allowed: bool
    canonical_identity: str | None = None


def _stop(disposition: str) -> PreflightResult:
    return PreflightResult(disposition, False)


def preflight_branch_create(
    *,
    intended_sha: str,
    existing_sha: str | None,
    idempotent: bool = True,
    authority_current: bool = True,
    targeted_lookup_available: bool = True,
) -> PreflightResult:
    if not authority_current:
        return _stop(AUTHORITY_DRIFT)
    if not targeted_lookup_available:
        return _stop(CAPABILITY_UNAVAILABLE)
    if existing_sha is None:
        return PreflightResult(ELIGIBLE, True)
    if existing_sha == intended_sha and idempotent:
        return _stop(ALREADY_SATISFIED)
    return _stop(CONFLICT)


def preflight_pr_create(
    *,
    base_exists: bool,
    head_exists: bool,
    has_eligible_diff: bool,
    existing_pr: Mapping[str, object] | None = None,
    intended_base: str,
    intended_head: str,
    authority_current: bool = True,
    targeted_lookup_available: bool = True,
) -> PreflightResult:
    if not authority_current:
        return _stop(AUTHORITY_DRIFT)
    if not targeted_lookup_available:
        return _stop(CAPABILITY_UNAVAILABLE)
    if not base_exists or not head_exists or not has_eligible_diff:
        return _stop(INVALID_HEAD_BASE)
    if existing_pr is None:
        return PreflightResult(ELIGIBLE, True)

    existing_base = str(existing_pr.get("base", ""))
    existing_head = str(existing_pr.get("head", ""))
    if existing_base == intended_base and existing_head == intended_head:
        identity = existing_pr.get("identity")
        return PreflightResult(
            DUPLICATE_EXACT,
            False,
            None if identity is None else str(identity),
        )
    return _stop(DUPLICATE_CONFLICT)


def preflight_durable_object(
    *,
    object_found: bool,
    protected_payload_matches: bool = False,
    canonical_identity: str | None = None,
    authority_current: bool = True,
    targeted_lookup_available: bool = True,
) -> PreflightResult:
    if not authority_current:
        return _stop(AUTHORITY_DRIFT)
    if not targeted_lookup_available:
        return _stop(CAPABILITY_UNAVAILABLE)
    if not object_found:
        return PreflightResult(ELIGIBLE, True)
    if protected_payload_matches:
        return PreflightResult(DUPLICATE_EXACT, False, canonical_identity)
    return _stop(DUPLICATE_CONFLICT)


def preflight_metadata_update(
    *,
    current: Mapping[str, object],
    intended: Mapping[str, object],
    conflict: bool = False,
    authority_current: bool = True,
    targeted_lookup_available: bool = True,
) -> PreflightResult:
    if not authority_current:
        return _stop(AUTHORITY_DRIFT)
    if not targeted_lookup_available:
        return _stop(CAPABILITY_UNAVAILABLE)
    if conflict:
        return _stop(CONFLICT)
    if all(current.get(key) == value for key, value in intended.items()):
        return _stop(ALREADY_SATISFIED)
    return PreflightResult(ELIGIBLE, True)
