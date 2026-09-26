from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

SCHEMA_ID = "rozkalns.agent-bootstrap.v1"
TOP_LEVEL_FIELDS = {
    "schema",
    "repository",
    "shared_policy",
    "rules",
    "continuation",
    "automation",
    "deployment_profile",
}
FORBIDDEN_MUTABLE_KEYS = {
    "current_main_sha",
    "main_sha",
    "current_branch_sha",
    "branch_sha",
    "current_head_sha",
    "head_sha",
    "active_pr_number",
    "pr_number",
    "ci_status",
    "check_status",
    "review_state",
    "mergeability",
    "runtime_revision",
    "deployed_revision",
    "merge_authorization",
    "live_authorization",
    "authorization_consumed",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "password",
    "api_key",
}
QUEUE_MODES = {"inactive", "supported", "not-applicable"}
DEPLOYMENT_PROFILES = {"simple-deploy", "github-only", "source-only", "custom", "none"}
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SECTION_RE = re.compile(r"^[A-Za-z0-9._/-]+#[a-z0-9][a-z0-9-]*$")
_ISSUE_RE = re.compile(r"^[1-9][0-9]*$")


class ManifestValidationError(ValueError):
    pass


@dataclass(frozen=True)
class BootstrapResolution:
    status: str
    rules_path: str | None
    reason: str | None = None


def _is_safe_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 256:
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    parts = path.parts
    if not parts or ".." in parts:
        return False
    return all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) is not None for part in parts)


def _reject_forbidden_keys(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).casefold()
            if normalized in FORBIDDEN_MUTABLE_KEYS:
                raise ManifestValidationError(f"forbidden mutable/secret field at {path}.{key}")
            _reject_forbidden_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_keys(nested, f"{path}[{index}]")


def _require_exact_keys(mapping: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ManifestValidationError(
            f"{path} keys mismatch; missing={missing or '-'} extra={extra or '-'}"
        )


def validate_manifest(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> None:
    if not isinstance(manifest, Mapping):
        raise ManifestValidationError("manifest must be an object")

    _reject_forbidden_keys(manifest)
    _require_exact_keys(manifest, TOP_LEVEL_FIELDS, "$")

    if manifest["schema"] != SCHEMA_ID:
        raise ManifestValidationError("schema identity mismatch")
    if not isinstance(manifest["repository"], str) or not _REPOSITORY_RE.fullmatch(
        manifest["repository"]
    ):
        raise ManifestValidationError("repository must be owner/name")

    shared_policy = manifest["shared_policy"]
    if not isinstance(shared_policy, Mapping):
        raise ManifestValidationError("shared_policy must be an object")
    _require_exact_keys(
        shared_policy, {"work_cycle", "github_api_access"}, "$.shared_policy"
    )
    for key in ("work_cycle", "github_api_access"):
        if not _is_safe_repo_path(shared_policy[key]):
            raise ManifestValidationError(f"unsafe shared policy path: {key}")

    rules = manifest["rules"]
    if not isinstance(rules, Mapping):
        raise ManifestValidationError("rules must be an object")
    _require_exact_keys(rules, {"primary", "local_strict_rules"}, "$.rules")
    if not _is_safe_repo_path(rules["primary"]):
        raise ManifestValidationError("unsafe primary rules path")
    strict_rules = rules["local_strict_rules"]
    if not isinstance(strict_rules, list) or len(strict_rules) > 32:
        raise ManifestValidationError("local_strict_rules must be a list with <=32 items")
    if len(strict_rules) != len(set(strict_rules)):
        raise ManifestValidationError("local_strict_rules must be unique")
    for locator in strict_rules:
        if not isinstance(locator, str) or not _SECTION_RE.fullmatch(locator):
            raise ManifestValidationError(f"invalid local strict-rule locator: {locator!r}")

    continuation = manifest["continuation"]
    if not isinstance(continuation, Mapping):
        raise ManifestValidationError("continuation must be an object")
    kind = continuation.get("kind")
    if kind == "issue":
        _require_exact_keys(continuation, {"kind", "locator"}, "$.continuation")
        if not isinstance(continuation["locator"], str) or not _ISSUE_RE.fullmatch(
            continuation["locator"]
        ):
            raise ManifestValidationError("issue continuation locator must be a positive issue number")
    elif kind == "file":
        _require_exact_keys(continuation, {"kind", "locator"}, "$.continuation")
        if not _is_safe_repo_path(continuation["locator"]):
            raise ManifestValidationError("unsafe continuation file path")
    elif kind == "none":
        _require_exact_keys(continuation, {"kind"}, "$.continuation")
    else:
        raise ManifestValidationError("continuation.kind must be issue, file, or none")

    automation = manifest["automation"]
    if not isinstance(automation, Mapping):
        raise ManifestValidationError("automation must be an object")
    _require_exact_keys(
        automation, {"fast_lane", "auto_run_full", "queue_mode"}, "$.automation"
    )
    if type(automation["fast_lane"]) is not bool or type(automation["auto_run_full"]) is not bool:
        raise ManifestValidationError("automation booleans must be boolean")
    if automation["queue_mode"] not in QUEUE_MODES:
        raise ManifestValidationError("invalid queue_mode")

    if manifest["deployment_profile"] not in DEPLOYMENT_PROFILES:
        raise ManifestValidationError("invalid deployment_profile")

    if repo_root is not None:
        root = repo_root.resolve()
        reference_paths = [
            rules["primary"],
            shared_policy["work_cycle"],
            shared_policy["github_api_access"],
        ]
        if kind == "file":
            reference_paths.append(continuation["locator"])
        for relative in reference_paths:
            candidate = (root / relative).resolve()
            if root not in candidate.parents and candidate != root:
                raise ManifestValidationError(f"reference escapes repository root: {relative}")
            if not candidate.is_file():
                raise ManifestValidationError(f"referenced canonical surface missing: {relative}")


def load_manifest(path: Path, *, repo_root: Path | None = None) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(str(exc)) from exc
    validate_manifest(data, repo_root=repo_root)
    return data


def resolve_bootstrap(
    repo_root: Path,
    *,
    manifest_relative_path: str = ".github/agent-bootstrap.json",
) -> BootstrapResolution:
    root = repo_root.resolve()
    fallback = root / "AGENTS.md"
    manifest_path = root / manifest_relative_path

    if not manifest_path.is_file():
        if fallback.is_file():
            return BootstrapResolution("LEGACY_FALLBACK", "AGENTS.md", "manifest absent")
        return BootstrapResolution("STOP_AMBIGUOUS", None, "manifest and AGENTS.md absent")

    try:
        manifest = load_manifest(manifest_path, repo_root=root)
    except ManifestValidationError as exc:
        if fallback.is_file():
            return BootstrapResolution(
                "MANIFEST_INVALID_FALLBACK", "AGENTS.md", str(exc)
            )
        return BootstrapResolution("STOP_AMBIGUOUS", None, str(exc))

    return BootstrapResolution("MANIFEST_ROUTED", manifest["rules"]["primary"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BOOTSTRAP_MANIFEST_V1")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest, repo_root=args.repo_root)
    except ManifestValidationError as exc:
        print(f"BOOTSTRAP_MANIFEST_V1=FAIL reason={exc}")
        return 1

    print(
        "BOOTSTRAP_MANIFEST_V1=PASS "
        f"repository={manifest['repository']} "
        f"rules={manifest['rules']['primary']} "
        f"continuation={manifest['continuation']['kind']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
