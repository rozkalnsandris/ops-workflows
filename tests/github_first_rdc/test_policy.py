from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "policy/github-first-rdc-fallback-v1.json"
NORMATIVE = ROOT / "docs/GITHUB_FIRST_RDC_FALLBACK_V1.md"
PARENT = ROOT / "docs/AGENT_WORK_CYCLE_V1.md"
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"
CYCLE = ROOT / "policy/agent-work-cycle-v1.json"


def route(case: dict) -> str:
    # The order is intentional: permission/tool errors cannot be upgraded to RDC authority.
    if case["github_error"]:
        return "STOP"
    if case["github_capable"]:
        return "GITHUB"
    if case["github_ci_capable"]:
        return "GITHUB_ACTIONS"
    if case["host_only"] and case["authority"]:
        return "RDC_EXCEPTION"
    return "STOP"


class GitHubFirstRdcFallbackPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.cycle = json.loads(CYCLE.read_text(encoding="utf-8"))
        cls.doc = NORMATIVE.read_text(encoding="utf-8")
        cls.parent = PARENT.read_text(encoding="utf-8")
        cls.agents = AGENTS.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")

    def test_canonical_identity_and_consumer_boundary(self) -> None:
        self.assertEqual("rozkalns.github-first-rdc-fallback.v1", self.policy["schema"])
        self.assertEqual("rozkalnsandris/ops-workflows", self.policy["canonical_repository"])
        adoption = self.policy["adoption"]
        self.assertTrue(adoption["consumer_repo_local_review_required"])
        self.assertFalse(adoption["shared_merge_auto_activates_consumers"])
        self.assertTrue(adoption["repo_local_stricter_rules_win"])
        self.assertTrue(adoption["github_only_deferred_live_mode_is_distinct"])

    def test_github_is_mandatory_when_available(self) -> None:
        selection = self.policy["selection"]
        self.assertEqual([
            "GITHUB_CONNECTED_TOOLS",
            "GITHUB_HOSTED_CI_WHEN_APPLICABLE",
            "MINIMAL_AUTHORIZED_RDC_IF_GITHUB_INCAPABLE",
            "STOP",
        ], selection["order"])
        self.assertTrue(selection["per_step_classification_required"])
        self.assertTrue(selection["github_capable_means_github_required"])
        self.assertFalse(selection["convenience_speed_or_habit_allows_rdc"])
        self.assertTrue(selection["rdc_never_replaces_supported_github_native_operation"])
        self.assertTrue(selection["github_actions_preferred_for_safe_source_tests_when_available"])
        self.assertIn("COMMIT", selection["github_native_operations"])
        self.assertIn("PULL_REQUEST", selection["github_native_operations"])

    def test_rdc_requires_proof_and_exact_authority(self) -> None:
        exc = self.policy["rdc_exception"]
        for name in (
            "exact_github_capability_gap_required",
            "github_ci_substitute_ruled_out_when_applicable",
            "appropriate_host_local_step_required",
            "narrowest_necessary_operation_only",
            "owner_authority_for_actual_mutation_required",
            "exception_record_required",
            "rdc_is_not_canonical_source_or_authorization",
        ):
            self.assertTrue(exc[name], name)
        self.assertEqual(["GITHUB", "MINIMAL_RDC", "GITHUB"], exc["before_and_after"])
        self.assertEqual(8, len(self.policy["exception_evidence_fields"]))

    def test_github_errors_must_never_trigger_rdc_retry(self) -> None:
        guards = self.policy["guardrails"]
        for name in (
            "github_access_denied_is_not_rdc_authority",
            "github_rate_limit_is_not_rdc_authority",
            "github_tool_error_is_not_rdc_authority",
            "uncertain_github_mutation_must_stop",
            "no_implicit_merge_live_deploy_settings_secrets_or_permissions_authority",
            "no_implicit_retry_rollback_cleanup_authority",
            "no_protected_data_in_public_evidence",
        ):
            self.assertTrue(guards[name], name)
        self.assertFalse(guards["rdc_duplicate_github_mutation_allowed"])

    def test_all_machine_decision_scenarios(self) -> None:
        cases = self.policy["decision_cases"]
        self.assertGreaterEqual(len(cases), 7)
        self.assertEqual(len(cases), len({c["scenario"] for c in cases}))
        for case in cases:
            with self.subTest(case=case["scenario"]):
                self.assertEqual(case["expected"], route(case))

    def test_human_and_parent_surfaces_are_consistent(self) -> None:
        for marker in (
            "GitHub-first / RDC fallback v1",
            "GitHub -> minimal RDC -> GitHub",
            "exception record",
            "does not automatically",
        ):
            self.assertIn(marker, self.doc)
        for marker in (
            "docs/GITHUB_FIRST_RDC_FALLBACK_V1.md",
            "policy/github-first-rdc-fallback-v1.json",
        ):
            self.assertIn(marker, self.parent)
            self.assertIn(marker, self.agents)
            self.assertIn(marker, self.readme)
        priority = self.cycle["tool_transport_priority"]
        self.assertTrue(priority["github_required_when_equivalent_capability_exists"])
        self.assertTrue(priority["rdc_capability_gap_evidence_required"])
        self.assertTrue(priority["github_tool_error_is_not_rdc_fallback"])
        self.assertEqual("policy/github-first-rdc-fallback-v1.json", priority["detailed_machine_contract"])


if __name__ == "__main__":
    unittest.main()
