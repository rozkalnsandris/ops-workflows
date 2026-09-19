from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_dependency_workflow_hardening import (
    validate_documentation,
    validate_renovate,
    validate_root,
    validate_workflow_security,
)


ROOT = Path(__file__).resolve().parents[2]


class DependencyWorkflowHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads((ROOT / "policy" / "dependency-workflow-hardening-v1.json").read_text(encoding="utf-8"))
        cls.renovate = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
        cls.workflow = (ROOT / ".github" / "workflows" / "workflow-security.yml").read_text(encoding="utf-8")

    def test_repository_contract_passes(self) -> None:
        validate_root(ROOT)

    def test_rejects_top_level_automerge(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["automerge"] = True
        with self.assertRaisesRegex(ValueError, "automerge"):
            validate_renovate(config, self.policy)

    def test_rejects_package_rule_automerge(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][0]["automerge"] = True
        with self.assertRaisesRegex(ValueError, "automerge"):
            validate_renovate(config, self.policy)

    def test_rejects_major_without_dashboard_approval(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][1]["dependencyDashboardApproval"] = False
        with self.assertRaisesRegex(ValueError, "Dashboard approval"):
            validate_renovate(config, self.policy)

    def test_rejects_dashboard_default_removal(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["dependencyDashboardApproval"] = False
        with self.assertRaisesRegex(ValueError, "fail-closed default"):
            validate_renovate(config, self.policy)

    def test_rejects_major_dashboard_bypass(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][0]["matchUpdateTypes"].append("major")
        with self.assertRaisesRegex(ValueError, "major Action updates"):
            validate_renovate(config, self.policy)

    def test_rejects_incompatible_pr_creation_mode(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["prCreation"] = "approval"
        with self.assertRaisesRegex(ValueError, "PR creation mode"):
            validate_renovate(config, self.policy)

    def test_rejects_github_runner_updates(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][2]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "runner updates"):
            validate_renovate(config, self.policy)

    def test_rejects_partial_zizmor_renovate_updates(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][3]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "zizmor action Renovate updates"):
            validate_renovate(config, self.policy)

    def test_rejects_partial_zizmor_engine_renovate_updates(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["packageRules"][4]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "zizmor engine Renovate updates"):
            validate_renovate(config, self.policy)

    def test_rejects_vulnerability_alert_scope_expansion(self) -> None:
        config = copy.deepcopy(self.renovate)
        config["vulnerabilityAlerts"]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "vulnerability alerts"):
            validate_renovate(config, self.policy)

    def test_rejects_zizmor_mutable_engine_version(self) -> None:
        workflow = self.workflow.replace('version: "1.29.0"', 'version: "latest"')
        with self.assertRaisesRegex(ValueError, "engine version"):
            validate_workflow_security(workflow, self.policy)

    def test_rejects_zizmor_advanced_security_permission_expansion(self) -> None:
        workflow = self.workflow.replace('advanced-security: "false"', 'advanced-security: "true"')
        with self.assertRaisesRegex(ValueError, "Advanced Security"):
            validate_workflow_security(workflow, self.policy)

    def test_rejects_secret_inheritance(self) -> None:
        workflow = self.workflow + "\nsecrets: inherit\n"
        with self.assertRaisesRegex(ValueError, "inherit secrets"):
            validate_workflow_security(workflow, self.policy)

    def test_rejects_missing_zizmor_companion_documentation(self) -> None:
        doc = (ROOT / "docs" / "DEPENDENCY_WORKFLOW_HARDENING_V1.md").read_text(encoding="utf-8")
        doc = doc.replace(
            "Renovate does not update this action or its `ghcr.io/zizmorcore/zizmor` `uses-with` engine input independently",
            "Renovate may update this action independently",
        )
        with self.assertRaisesRegex(ValueError, "documentation missing governance marker"):
            validate_documentation(doc)

    def test_rejects_missing_major_reconciliation_boundary_documentation(self) -> None:
        doc = (ROOT / "docs" / "DEPENDENCY_WORKFLOW_HARDENING_V1.md").read_text(encoding="utf-8")
        doc = doc.replace("Dependency Dashboard approval is a creation gate.", "Dependency Dashboard approval is retroactive.")
        with self.assertRaisesRegex(ValueError, "documentation missing governance marker"):
            validate_documentation(doc)


if __name__ == "__main__":
    unittest.main()
