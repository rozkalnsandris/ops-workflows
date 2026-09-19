#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
USES_LINE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(?:\s+#\s*(\S+))?\s*$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"missing file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def validate_renovate(config: dict, policy: dict) -> None:
    expected = policy["renovate"]
    require(config.get("enabledManagers") == expected["enabled_managers"], "Renovate manager scope drift")
    require(config.get("automerge") is expected["automerge"], "Renovate automerge must stay disabled")
    require(config.get("platformAutomerge") is expected["platform_automerge"], "platform automerge must stay disabled")
    require(config.get("dependencyDashboard") is expected["dependency_dashboard"], "Dependency Dashboard invariant changed")
    require(
        config.get("dependencyDashboardApproval") is expected["dependency_dashboard_approval_default"],
        "Dependency Dashboard approval must be the fail-closed default",
    )
    require(config.get("prCreation") == expected["pr_creation"], "Renovate PR creation mode drift")
    require(config.get("branchConcurrentLimit") == expected["branch_concurrent_limit"], "Renovate branch concurrency changed")
    require(config.get("prConcurrentLimit") == expected["pr_concurrent_limit"], "Renovate PR concurrency changed")
    require(config.get("prHourlyLimit") == expected["pr_hourly_limit"], "Renovate PR hourly limit changed")
    require(config.get("commitHourlyLimit") == expected["commit_hourly_limit"], "Renovate commit hourly limit changed")
    require(config.get("configMigration") is False, "Renovate config migration must stay disabled in the first slice")
    require(config.get("rebaseWhen") == "conflicted", "Renovate automatic rebasing scope changed")

    vulnerability_alerts = config.get("vulnerabilityAlerts")
    require(isinstance(vulnerability_alerts, dict), "Renovate vulnerabilityAlerts boundary missing")
    require(vulnerability_alerts.get("enabled") is expected["vulnerability_alerts"], "Renovate vulnerability alerts must stay disabled")

    extends = config.get("extends")
    require(isinstance(extends, list), "Renovate extends must be a list")
    require("config:recommended" in extends, "Renovate recommended preset missing")
    require("helpers:pinGitHubActionDigests" in extends, "GitHub Action digest pinning preset missing")

    package_rules = config.get("packageRules")
    require(isinstance(package_rules, list) and package_rules, "Renovate package rules missing")
    require(len(package_rules) == 5, "unexpected Renovate package rule requires policy review")
    major_rules: list[dict] = []
    dashboard_bypass_rules: list[dict] = []
    runner_hold_rules: list[dict] = []
    zizmor_hold_rules: list[dict] = []
    zizmor_engine_hold_rules: list[dict] = []
    for rule in package_rules:
        require(isinstance(rule, dict), "Renovate package rule must be an object")
        require(rule.get("matchManagers") == expected["enabled_managers"], "package rule manager scope drift")
        require(rule.get("automerge") is not True, "package rule may not enable automerge")
        update_types = rule.get("matchUpdateTypes", [])
        require(isinstance(update_types, list), "package rule update types must be a list")
        if any(update_type in expected["major_update_types"] for update_type in update_types):
            require(rule.get("dependencyDashboardApproval") is True, "major Action updates require Dashboard approval")
            require(rule.get("enabled") is not False, "major Action updates may not be silently disabled")
            major_rules.append(rule)
        if rule.get("dependencyDashboardApproval") is False:
            require(update_types, "Dashboard bypass rule must name its allowed update types")
            require(
                set(update_types).issubset(expected["dashboard_bypass_update_types"]),
                "Dashboard bypass may only cover approved non-major update types",
            )
            dashboard_bypass_rules.append(rule)
        if expected["github_runner_dep_type"] in rule.get("matchDepTypes", []):
            require(rule.get("matchDepTypes") == [expected["github_runner_dep_type"]], "runner hold must be exact")
            require(rule.get("enabled") is expected["github_runner_updates_enabled"], "GitHub runner updates must stay disabled")
            runner_hold_rules.append(rule)
        if expected["zizmor_action_package"] in rule.get("matchPackageNames", []):
            require(rule.get("matchPackageNames") == [expected["zizmor_action_package"]], "zizmor hold must be exact")
            require(
                rule.get("enabled") is expected["zizmor_action_renovate_updates_enabled"],
                "zizmor action Renovate updates must stay disabled",
            )
            zizmor_hold_rules.append(rule)
        if expected["zizmor_engine_package"] in rule.get("matchPackageNames", []):
            require(rule.get("matchPackageNames") == [expected["zizmor_engine_package"]], "zizmor engine hold must be exact")
            require(
                rule.get("matchDepTypes") == [expected["zizmor_engine_dep_type"]],
                "zizmor engine hold dependency type drift",
            )
            require(
                rule.get("enabled") is expected["zizmor_engine_renovate_updates_enabled"],
                "zizmor engine Renovate updates must stay disabled",
            )
            zizmor_engine_hold_rules.append(rule)

    require(
        len(major_rules) == 1 and expected["major_updates_require_dashboard_approval"],
        "major-update approval invariant changed",
    )
    require(len(dashboard_bypass_rules) == 1, "expected one explicit non-major Dashboard bypass rule")
    require(
        dashboard_bypass_rules[0].get("matchUpdateTypes") == expected["dashboard_bypass_update_types"],
        "Dashboard bypass update types drift",
    )
    require(len(runner_hold_rules) == 1, "GitHub runner hold rule missing")
    require(len(zizmor_hold_rules) == 1, "zizmor action hold rule missing")
    require(len(zizmor_engine_hold_rules) == 1, "zizmor engine hold rule missing")


def validate_workflow_security(text: str, policy: dict) -> None:
    static = policy["workflow_static_analysis"]
    require("workflow_call:" in text, "workflow security guard must remain reusable")
    require("permissions:\n  contents: read" in text, "workflow security permissions must remain contents: read")
    require("self-hosted" not in text, "workflow security guard may not use self-hosted runners")
    require("secrets: inherit" not in text, "workflow security guard may not inherit secrets")
    require("security-events: write" not in text, "workflow security guard may not require security-events write")
    require("permissions: write-all" not in text, "workflow security guard may not use write-all")
    require("--fix" not in text, "zizmor auto-fix is outside the reviewed guard")

    actionlint = static["actionlint"]
    require(f'ACTIONLINT_VERSION: "{actionlint["version"]}"' in text, "actionlint version drift")
    require(actionlint["linux_amd64_archive_sha256"] in text, "actionlint checksum drift")

    zizmor = static["zizmor"]
    require(f'zizmorcore/zizmor-action@{zizmor["action_sha"]} # {zizmor["action_version"]}' in text, "zizmor action identity drift")
    require(f'version: "{zizmor["engine_version"]}"' in text, "zizmor engine version drift")
    require('online-audits: "false"' in text, "zizmor online audits must stay disabled")
    require('advanced-security: "false"' in text, "zizmor must not expand Advanced Security permissions")
    require('annotations: "true"' in text, "zizmor annotations must remain enabled")


def validate_external_uses_tracking(root: Path) -> None:
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    require(workflows, "no workflows found")

    errors: list[str] = []
    for path in workflows:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES_LINE.match(line)
            if not match:
                continue
            target, tracked_ref = match.groups()
            if target.startswith("./") or target.startswith("docker://"):
                continue
            if "@" not in target:
                errors.append(f"{path}:{number}: external uses target has no revision")
                continue
            _, revision = target.rsplit("@", 1)
            if not FULL_SHA.fullmatch(revision):
                errors.append(f"{path}:{number}: external uses target is not pinned to a full SHA")
                continue
            if not tracked_ref:
                errors.append(f"{path}:{number}: digest-pinned external uses target has no Renovate tracking comment")

    require(not errors, "Renovate tracking invariant failed:\n- " + "\n- ".join(errors))


def validate_documentation(text: str) -> None:
    for marker in (
        "Dependency Dashboard approval is the fail-closed default for every GitHub Actions update",
        "GitHub-hosted runner labels (`github-runner`, including Ubuntu labels) are disabled",
        "`zizmorcore/zizmor-action` and its separate `ghcr.io/zizmorcore/zizmor` `uses-with` engine input are both disabled",
        "Dependency Dashboard approval is a creation gate.",
        "Renovate does not update this action or its `ghcr.io/zizmorcore/zizmor` `uses-with` engine input independently",
    ):
        require(marker in text, f"hardening documentation missing governance marker: {marker}")


def validate_root(root: Path) -> None:
    policy = load_json(root / "policy" / "dependency-workflow-hardening-v1.json")
    require(policy.get("schema_version") == 1, "dependency workflow policy schema mismatch")
    require(policy.get("policy") == "DEPENDENCY_WORKFLOW_HARDENING_V1", "dependency workflow policy id mismatch")
    require(policy.get("canonical_repository") == "rozkalnsandris/ops-workflows", "canonical repository changed")

    config = load_json(root / "renovate.json")
    validate_renovate(config, policy)

    workflow_path = root / policy["workflow_static_analysis"]["reusable_workflow"]
    require(workflow_path.is_file(), f"missing reusable workflow: {workflow_path}")
    validate_workflow_security(workflow_path.read_text(encoding="utf-8"), policy)
    validate_external_uses_tracking(root)

    doc = root / "docs" / "DEPENDENCY_WORKFLOW_HARDENING_V1.md"
    require(doc.is_file() and doc.stat().st_size > 0, "hardening documentation missing")
    validate_documentation(doc.read_text(encoding="utf-8"))

    boundaries = policy["boundaries"]
    for key in (
        "shared_workflow_mutates_repository",
        "shared_workflow_mutates_runtime",
        "shared_workflow_inherits_secrets",
        "renovate_pr_is_merge_authority",
        "renovate_app_install_is_source_change",
        "merge_authorizes_live",
    ):
        require(boundaries.get(key) is False, f"boundary must remain false: {key}")
    require(boundaries.get("repository_local_stricter_rules_win") is True, "local stricter-rule precedence changed")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    try:
        validate_root(root.resolve())
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"DEPENDENCY_WORKFLOW_HARDENING=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print("DEPENDENCY_WORKFLOW_HARDENING=PASS")
