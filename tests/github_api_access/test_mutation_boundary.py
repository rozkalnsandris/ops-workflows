from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "policy" / "github-api-access-v1.json"
DOC_PATH = ROOT / "docs" / "GITHUB_API_ACCESS_V1.md"
WORK_CYCLE_PATH = ROOT / "docs" / "AGENT_WORK_CYCLE_V1.md"


class GitHubApiMutationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.doc = DOC_PATH.read_text(encoding="utf-8")
        cls.work_cycle = WORK_CYCLE_PATH.read_text(encoding="utf-8")

    def test_slice_tracking_is_explicit(self):
        self.assertEqual(111, self.policy["tracking"]["mutation_boundary_issue"])

    def test_final_pre_mutation_refresh_is_compact_and_exact_head_bound(self):
        boundary = self.policy["mutation_boundary"]
        self.assertEqual("FINAL_PREMERGE_COMPACT", boundary["final_pre_mutation_budget_class"])
        self.assertEqual(
            {
                "CURRENT_MAIN_OR_BASE",
                "EXACT_PR_HEAD",
                "MERGEABILITY",
                "REQUIRED_EXACT_HEAD_CI_OR_STATUS",
                "REVIEWS",
                "UNRESOLVED_REVIEW_THREADS",
                "EXACT_AUTHORITY_BINDING",
            },
            set(boundary["final_pre_mutation_facts"]),
        )
        self.assertFalse(boundary["broad_repo_audit_before_mutation_allowed"])
        self.assertTrue(boundary["expected_head_binding_required_when_supported"])

    def test_stable_mutation_outcome_dispositions(self):
        self.assertEqual(
            {
                "MUTATION_CONFIRMED_SUCCESS",
                "MUTATION_CONFIRMED_REJECTED_BEFORE_APPLY",
                "MUTATION_OUTCOME_UNKNOWN_RATE_LIMIT",
                "MUTATION_OUTCOME_UNKNOWN_TIMEOUT",
                "MUTATION_OUTCOME_UNKNOWN_TRANSPORT",
                "POST_MUTATION_RECONCILIATION_REQUIRED",
            },
            set(self.policy["mutation_outcome_dispositions"]),
        )

    def test_authorization_is_consumed_at_dispatch_and_ambiguity_is_fail_closed(self):
        boundary = self.policy["mutation_boundary"]
        self.assertTrue(boundary["authorization_consumed_when_mutation_dispatched"])
        self.assertTrue(boundary["post_dispatch_uncertainty_fail_closed"])
        self.assertTrue(boundary["stop_after_ambiguous_outcome"])
        self.assertTrue(boundary["minimal_read_only_reconciliation_only"])

    def test_429_timeout_transport_never_allow_duplicate_mutation(self):
        boundary = self.policy["mutation_boundary"]
        self.assertFalse(boundary["automatic_duplicate_mutation_after_429"])
        self.assertFalse(boundary["automatic_duplicate_mutation_after_timeout"])
        self.assertFalse(boundary["automatic_duplicate_mutation_after_transport_error"])
        self.assertFalse(boundary["automatic_duplicate_mutation_after_malformed_or_partial_response"])
        self.assertFalse(boundary["http_429_proves_mutation_not_applied"])
        self.assertFalse(boundary["alternate_endpoint_or_tool_retry_after_dispatch_allowed"])
        self.assertFalse(boundary["rollback_cleanup_rebase_reset_after_ambiguity_allowed"])

    def test_exact_head_success_and_head_drift_fixtures(self):
        scenarios = self.policy["mutation_scenarios"]
        success = scenarios["EXACT_HEAD_GUARDED_SUCCESS"]
        self.assertTrue(success["mutation_dispatched"])
        self.assertEqual("MUTATION_CONFIRMED_SUCCESS", success["disposition"])
        self.assertFalse(success["automatic_duplicate_mutation_allowed"])
        self.assertEqual("EXACT_MAIN_MINIMAL", success["post_result_budget_class"])

        drift = scenarios["HEAD_DRIFT_PRE_DISPATCH"]
        self.assertFalse(drift["mutation_dispatched"])
        self.assertEqual("MUTATION_CONFIRMED_REJECTED_BEFORE_APPLY", drift["disposition"])
        self.assertFalse(drift["automatic_duplicate_mutation_allowed"])

    def test_primary_rate_limit_before_dispatch_uses_read_backoff_lane(self):
        scenario = self.policy["mutation_scenarios"]["PRIMARY_RATE_LIMIT_PRE_DISPATCH"]
        self.assertFalse(scenario["mutation_dispatched"])
        self.assertTrue(scenario["read_backoff_may_apply"])
        self.assertFalse(scenario["automatic_duplicate_mutation_allowed"])

    def test_ambiguous_post_dispatch_fixtures_require_reconciliation(self):
        scenarios = self.policy["mutation_scenarios"]
        expected = {
            "HTTP_429_POST_DISPATCH": "MUTATION_OUTCOME_UNKNOWN_RATE_LIMIT",
            "TIMEOUT_POST_DISPATCH": "MUTATION_OUTCOME_UNKNOWN_TIMEOUT",
            "TRANSPORT_ERROR_POST_DISPATCH": "MUTATION_OUTCOME_UNKNOWN_TRANSPORT",
        }
        for name, disposition in expected.items():
            scenario = scenarios[name]
            self.assertTrue(scenario["mutation_dispatched"])
            self.assertEqual(disposition, scenario["disposition"])
            self.assertFalse(scenario["automatic_duplicate_mutation_allowed"])
            self.assertTrue(scenario["requires_reconciliation"])

    def test_next_sync_reconciliation_never_revives_consumed_authority(self):
        reconciliation = self.policy["post_mutation_reconciliation"]
        self.assertTrue(reconciliation["next_sync_requires_fresh_canonical_reconciliation"])
        self.assertEqual(
            "MUTATION_CONFIRMED_SUCCESS",
            reconciliation["expected_head_merged_and_lineage_correct"],
        )
        self.assertFalse(reconciliation["expected_head_not_merged_consumed_authority_revives"])
        self.assertTrue(reconciliation["expected_head_not_merged_requires_fresh_authority"])
        self.assertTrue(reconciliation["ambiguous_or_drifted_state_remains_stopped"])

        applied = self.policy["mutation_scenarios"]["NEXT_SYNC_PROVES_APPLIED"]
        self.assertFalse(applied["automatic_duplicate_mutation_allowed"])
        self.assertFalse(applied["fresh_authority_required"])

        not_applied = self.policy["mutation_scenarios"]["NEXT_SYNC_PROVES_NOT_APPLIED"]
        self.assertFalse(not_applied["automatic_duplicate_mutation_allowed"])
        self.assertTrue(not_applied["fresh_authority_required"])

    def test_confirmed_success_reconciliation_is_minimum_sufficient(self):
        reconciliation = self.policy["post_mutation_reconciliation"]
        self.assertEqual("EXACT_MAIN_MINIMAL", reconciliation["confirmed_success_budget_class"])
        self.assertFalse(reconciliation["confirmed_success_deep_audit_by_default"])
        self.assertTrue(reconciliation["deeper_retrieval_only_on_verification_failure_or_drift"])

    def test_merge_success_never_grants_live_authority(self):
        self.assertFalse(self.policy["mutation_boundary"]["merge_success_implies_live_or_deploy_authority"])
        self.assertFalse(self.policy["authority"]["changes_live_authority"])
        self.assertFalse(self.policy["authority"]["changes_deploy_authority"])

    def test_human_contract_documents_mutation_boundary_and_reconciliation(self):
        for marker in (
            "## Final pre-mutation gate",
            "## Mutation outcome dispositions",
            "## Mutation boundary",
            "## Post-mutation reconciliation",
            "## Deterministic mutation scenarios",
        ):
            self.assertIn(marker, self.doc)
        self.assertIn("`429` must never be interpreted as proof", self.doc)
        self.assertIn("fresh authority required", self.doc)

    def test_active_work_cycle_already_requires_no_duplicate_mutation(self):
        self.assertIn("must not cause an automatic duplicate mutation", self.work_cycle)
        self.assertIn("preserve/reconcile only the minimum permitted evidence", self.work_cycle)


if __name__ == "__main__":
    unittest.main()
