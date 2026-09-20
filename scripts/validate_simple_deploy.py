#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TARGET_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
HEALTH_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")
FORBIDDEN_OPERATIONS = {
    "database-schema-data-mutation",
    "destructive-recovery",
    "secrets-credentials-permissions",
    "cloudflare-dns-network",
    "private-provider-activation",
    "unrelated-host-control",
}
TOP_LEVEL_KEYS = {
    "schema",
    "repository",
    "image",
    "build",
    "target",
    "compose",
    "health",
    "persistence",
    "registry",
    "forbidden_operations",
}


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    keys = set(value)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)
    require(not missing, f"{label} missing required fields: {', '.join(missing)}")
    require(not unknown, f"{label} contains forbidden/unknown fields: {', '.join(unknown)}")
    return value


def require_string(value: Any, label: str, *, maximum: int = 512) -> str:
    require(isinstance(value, str) and 0 < len(value) <= maximum, f"{label} must be a non-empty string")
    require("\n" not in value and "\r" not in value and "\x00" not in value, f"{label} contains forbidden control characters")
    return value


def safe_relative_path(value: Any, label: str, *, allow_dot: bool = False) -> str:
    path = require_string(value, label, maximum=256)
    if allow_dot and path == ".":
        return path
    require(not path.startswith(("/", "~", "\\")), f"{label} must be repository-relative")
    require("\\" not in path, f"{label} must use POSIX separators")
    parts = path.split("/")
    require(all(part and part not in {".", ".."} for part in parts), f"{label} may not contain dot traversal")
    require(all(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*", part) for part in parts), f"{label} contains an unsafe path segment")
    return path


def validate_manifest(manifest: dict[str, Any], expected_repository: str | None = None) -> dict[str, str]:
    require_exact_keys(manifest, TOP_LEVEL_KEYS, "manifest")
    require(manifest["schema"] == "rozkalns.simple-deploy.consumer.v1", "manifest schema identity mismatch")

    repository = require_string(manifest["repository"], "repository", maximum=256)
    require(REPOSITORY_RE.fullmatch(repository) is not None, "repository identity is invalid")
    if expected_repository is not None:
        require(repository == expected_repository, "manifest repository does not match caller repository")

    owner, repo = repository.split("/", 1)
    image = require_string(manifest["image"], "image", maximum=256)
    expected_image = f"ghcr.io/{owner.lower()}/{repo.lower()}"
    require(image == expected_image, f"image must be the caller-bound GHCR identity {expected_image}")

    build = require_exact_keys(manifest["build"], {"context", "dockerfile", "architecture"}, "build")
    build_context = safe_relative_path(build["context"], "build.context", allow_dot=True)
    dockerfile = safe_relative_path(build["dockerfile"], "build.dockerfile")
    require(build["architecture"] == "linux/arm64", "v1 architecture must be linux/arm64")

    target = require_exact_keys(manifest["target"], {"alias", "runtime_class"}, "target")
    target_alias = require_string(target["alias"], "target.alias", maximum=128)
    require(TARGET_RE.fullmatch(target_alias) is not None, "target.alias has invalid characters")
    require(target["runtime_class"] == "rpi5-compose", "v1 runtime_class must be rpi5-compose")

    compose = require_exact_keys(manifest["compose"], {"project", "file", "service"}, "compose")
    compose_project = require_string(compose["project"], "compose.project", maximum=128)
    require(NAME_RE.fullmatch(compose_project) is not None, "compose.project has invalid characters")
    compose_file = safe_relative_path(compose["file"], "compose.file")
    compose_service = require_string(compose["service"], "compose.service", maximum=128)
    require(NAME_RE.fullmatch(compose_service) is not None, "compose.service has invalid characters")

    health = require_exact_keys(manifest["health"], {"liveness_path", "readiness"}, "health")
    liveness = require_string(health["liveness_path"], "health.liveness_path", maximum=256)
    require(HEALTH_PATH_RE.fullmatch(liveness) is not None, "health.liveness_path must be a fixed local HTTP path")
    readiness = health["readiness"]
    require(isinstance(readiness, dict), "health.readiness must be an object")
    state = readiness.get("state")
    require(state in {"required", "not-applicable"}, "health.readiness.state is invalid")
    if state == "required":
        require_exact_keys(readiness, {"state", "path"}, "health.readiness")
        readiness_path = require_string(readiness["path"], "health.readiness.path", maximum=256)
        require(HEALTH_PATH_RE.fullmatch(readiness_path) is not None, "health.readiness.path must be a fixed local HTTP path")
    else:
        require_exact_keys(readiness, {"state"}, "health.readiness")
        readiness_path = ""

    persistence = require_exact_keys(manifest["persistence"], {"volumes"}, "persistence")
    volumes = persistence["volumes"]
    require(isinstance(volumes, list) and len(volumes) <= 32, "persistence.volumes must be an explicit bounded list")
    require(len(volumes) == len(set(volumes)), "persistence.volumes must not contain duplicates")
    for volume in volumes:
        require(isinstance(volume, str) and NAME_RE.fullmatch(volume) is not None, "persistence volume identity is invalid")

    registry = require_exact_keys(manifest["registry"], {"pull_profile"}, "registry")
    pull_profile = registry["pull_profile"]
    require(pull_profile in {"public-anonymous-pull", "private-read-only"}, "registry.pull_profile is invalid")

    forbidden = manifest["forbidden_operations"]
    require(isinstance(forbidden, list), "forbidden_operations must be a list")
    require(len(forbidden) == len(set(forbidden)), "forbidden_operations must not contain duplicates")
    require(set(forbidden) == FORBIDDEN_OPERATIONS, "forbidden_operations must contain the complete fixed v1 sensitive-operation exclusion set")

    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    manifest_sha256 = hashlib.sha256(canonical).hexdigest()
    return {
        "repository": repository,
        "image": image,
        "target_alias": target_alias,
        "build_context": build_context,
        "dockerfile": dockerfile,
        "architecture": "linux/arm64",
        "compose_project": compose_project,
        "compose_file": compose_file,
        "compose_service": compose_service,
        "liveness_path": liveness,
        "readiness_state": state,
        "readiness_path": readiness_path,
        "pull_profile": pull_profile,
        "persistence_json": json.dumps(volumes, sort_keys=True, separators=(",", ":")),
        "manifest_sha256": manifest_sha256,
    }


def load_object(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    require(policy.get("schema_version") == 1, "SIMPLE-DEPLOY policy schema mismatch")
    require(policy.get("policy") == "SIMPLE_DEPLOY_V1", "SIMPLE-DEPLOY policy id mismatch")
    require(policy.get("status") == "SHARED_SOURCE_CONTRACT_NOT_CONSUMER_ACTIVE", "SIMPLE-DEPLOY activation status drift")
    require(policy.get("canonical_repository") == "rozkalnsandris/ops-workflows", "canonical repository drift")
    require(policy.get("tracking_issue") == 97, "tracking issue drift")

    workflow = policy["workflow"]
    require(workflow["trigger"] == "workflow_call", "reusable workflow trigger changed")
    require(workflow["manifest_path"] == ".simple-deploy.json", "manifest path changed")
    require(workflow["github_hosted_runner"] == "ubuntu-24.04", "GitHub-hosted runner baseline changed")
    require(workflow["self_hosted_runner_allowed"] is False, "public self-hosted runner boundary changed")
    require(workflow["caller_permissions"] == {"contents": "read", "packages": "write"}, "caller permission contract changed")
    require(workflow["write_all_allowed"] is False, "write-all must stay forbidden")
    require(workflow["environment"] == "production", "production environment identity changed")
    require(workflow["manual_environment_reviewer_in_baseline"] is False, "baseline manual reviewer UX changed")
    require(workflow["concurrency_owner"] == "called_workflow", "production concurrency ownership changed")
    require(workflow["caller_generic_concurrency_allowed"] is False, "caller concurrency duplication must remain forbidden")
    require(workflow["shared_revision_source"] == "job.workflow_sha", "shared workflow identity source changed")

    identity = policy["identity"]
    for key in (
        "source_sha_must_equal_event_sha",
        "source_must_be_default_branch",
        "exact_sha_image_tag_required",
        "production_pointer_is_discovery_only",
        "build_once_promote_exact_digest",
        "pointer_must_resolve_to_built_digest",
    ):
        require(identity[key] is True, f"identity invariant changed: {key}")
    require(identity["canonical_deployment_identity"] == "immutable_registry_digest", "digest identity invariant changed")
    require(identity["production_pointer"] == "production", "production pointer changed")

    manifest = policy["manifest"]
    require(manifest["allowed_architectures"] == ["linux/arm64"], "v1 architecture set changed")
    require(manifest["runtime_class"] == "rpi5-compose", "runtime class changed")
    require(manifest["image_must_match_consumer_repository"] is True, "GHCR caller binding weakened")
    require(set(manifest["required_forbidden_operations"]) == FORBIDDEN_OPERATIONS, "sensitive-operation exclusions changed")

    boundaries = policy["boundaries"]
    for key in (
        "ops_workflows_executes_rpi5_mutation",
        "ops_workflows_stores_production_credentials",
        "workflow_accepts_arbitrary_shell_argv_or_environment",
        "workflow_accepts_arbitrary_host_path",
        "workflow_accepts_secret_values_in_manifest",
        "ordinary_deploy_includes_database_or_data_mutation",
        "ordinary_deploy_includes_network_or_cloudflare_mutation",
        "ordinary_deploy_includes_unrelated_host_control",
        "persistent_privileged_public_self_hosted_runner",
    ):
        require(boundaries[key] is False, f"trust boundary must remain false: {key}")
    require(boundaries["repository_local_stricter_rules_win"] is True, "local stricter-rule precedence changed")

    activation = policy["activation"]
    require(activation["shared_merge_auto_migrates_consumers"] is False, "shared merge must not auto-migrate consumers")
    require(activation["consumer_source_adoption_required"] is True, "consumer adoption must remain explicit")
    require(activation["one_time_runtime_cutover_required"] is True, "one-time runtime cutover must remain explicit")
    require(activation["ordinary_release_requires_fresh_live_after_cutover"] is False, "ordinary activated release must not add per-release LIVE")
    require(activation["sensitive_operations_remain_separately_gated"] is True, "sensitive operation gates changed")

    fleet = policy["fleet_upgrade"]
    require(fleet["consumer_pin_must_be_full_commit_sha"] is True, "consumer immutable pin requirement changed")
    require(fleet["renovate_version_comment_required"] is True, "Renovate tracking convention changed")
    require(fleet["mutable_main_tag_or_version_branch_forbidden"] is True, "mutable consumer pin became allowed")

    compat = policy["compatibility"]
    require(compat["auto_live_v1_primitives_reused"] is True, "Auto-Live compatibility changed")
    require(compat["simple_live_remains_for_sensitive_or_exceptional_operations"] is True, "Simple LIVE compatibility changed")
    require(compat["queue_vnext_issue"] == 96 and compat["queue_vnext_blocked_until_fleet_stable"] is True, "Queue vNext sequencing changed")


def validate_schema_contract(schema: dict[str, Any]) -> None:
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "consumer schema draft changed")
    require(schema.get("additionalProperties") is False, "consumer schema top-level unknown fields must fail closed")
    require(set(schema.get("required", [])) == TOP_LEVEL_KEYS, "consumer schema required fields drift")
    properties = schema.get("properties", {})
    require(set(properties) == TOP_LEVEL_KEYS, "consumer schema property set drift")
    for nested in ("build", "target", "compose", "health", "persistence", "registry"):
        require(properties[nested].get("additionalProperties") is False, f"consumer schema {nested} unknown fields must fail closed")
    require(properties["build"]["properties"]["architecture"].get("const") == "linux/arm64", "schema architecture changed")
    require(properties["target"]["properties"]["runtime_class"].get("const") == "rpi5-compose", "schema runtime class changed")
    forbidden_items = properties["forbidden_operations"]["items"].get("enum", [])
    require(set(forbidden_items) == FORBIDDEN_OPERATIONS, "schema sensitive-operation enum drift")


def validate_reusable_workflow(text: str) -> None:
    required_markers = (
        "workflow_call:",
        "source_sha:",
        "permissions:\n  contents: read\n  packages: write",
        "runs-on: ubuntu-24.04",
        "JOB_CONTEXT_JSON: ${{ toJSON(job) }}",
        "workflow_repository",
        "workflow_sha",
        "repository: ${{ steps.shared_identity.outputs.repository }}",
        "ref: ${{ steps.shared_identity.outputs.sha }}",
        "environment: production",
        "group: simple-deploy-${{ needs.validate.outputs.target_alias }}",
        "cancel-in-progress: false",
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
        "--metadata-file",
        "--prefer-index=false",
        '"${IMAGE}:${SOURCE_SHA}"',
        '"${IMAGE}:production"',
        "containerimage.digest",
        "rozkalns.simple-deploy.intent.v1",
        "manifest_sha256",
        "SHARED_SHA: ${{ needs.validate.outputs.shared_sha }}",
    )
    for marker in required_markers:
        require(marker in text, f"reusable workflow missing invariant marker: {marker}")
    for forbidden in (
        "self-hosted",
        "permissions: write-all",
        "secrets: inherit",
        "ssh ",
        "sudo ",
        "docker compose",
        "workflow_dispatch:",
    ):
        require(forbidden not in text, f"reusable workflow contains forbidden authority/surface: {forbidden}")


def validate_documentation(text: str) -> None:
    markers = (
        "SIMPLE-DEPLOY v1",
        "source contract; consumer activation is separate",
        "immutable full commit SHA",
        "# v1.0.0",
        "production` is discovery only",
        "exact resolved digest is the deployment identity",
        "environment: production",
        "called workflow owns production concurrency",
        "required reviewer is not part of the baseline",
        "public-anonymous-pull",
        "private-read-only",
        "RPi5_main#666",
        "rozkalns_weather#142",
        "Queue vNext #96",
        "database/schema/data",
        "Cloudflare/DNS/network",
    )
    for marker in markers:
        require(marker in text, f"SIMPLE-DEPLOY documentation missing marker: {marker}")


def validate_root(root: Path) -> None:
    policy = load_object(root / "policy" / "simple-deploy-v1.json")
    validate_policy(policy)
    schema = load_object(root / "policy" / "schemas" / "simple-deploy-consumer-v1.schema.json")
    validate_schema_contract(schema)

    workflow_path = root / ".github" / "workflows" / "simple-deploy.yml"
    require(workflow_path.is_file(), "missing reusable SIMPLE-DEPLOY workflow")
    validate_reusable_workflow(workflow_path.read_text(encoding="utf-8"))

    gate_path = root / ".github" / "workflows" / "simple-deploy-policy-gate.yml"
    require(gate_path.is_file(), "missing SIMPLE-DEPLOY policy gate")
    gate = gate_path.read_text(encoding="utf-8")
    require("python3 -m unittest -v tests.simple_deploy.test_contract" in gate, "policy gate must run focused SIMPLE-DEPLOY tests")
    require("python3 scripts/validate_simple_deploy.py --root ." in gate, "policy gate must validate repository contract")
    require("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in gate, "policy gate checkout pin drift")

    doc_path = root / "docs" / "SIMPLE_DEPLOY_V1.md"
    require(doc_path.is_file(), "missing normative SIMPLE-DEPLOY document")
    validate_documentation(doc_path.read_text(encoding="utf-8"))


def write_github_outputs(path: Path, outputs: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            require("\n" not in value and "\r" not in value, f"output {key} is not single-line safe")
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SIMPLE-DEPLOY v1 shared or consumer contract")
    parser.add_argument("--root", type=Path, help="validate the shared ops-workflows contract root")
    parser.add_argument("--manifest", type=Path, help="validate one consumer manifest")
    parser.add_argument("--expected-repository", help="bind manifest to the caller repository")
    parser.add_argument("--github-output", type=Path, help="append validated public-safe manifest outputs")
    args = parser.parse_args()

    try:
        if args.root:
            validate_root(args.root.resolve())
            print("SIMPLE_DEPLOY_SHARED_CONTRACT=PASS")
        if args.manifest:
            manifest = load_object(args.manifest)
            outputs = validate_manifest(manifest, args.expected_repository)
            if args.github_output:
                write_github_outputs(args.github_output, outputs)
            print("SIMPLE_DEPLOY_CONSUMER_MANIFEST=PASS")
        require(args.root is not None or args.manifest is not None, "one of --root or --manifest is required")
    except (ValidationError, json.JSONDecodeError, OSError) as exc:
        print(f"SIMPLE_DEPLOY=FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
