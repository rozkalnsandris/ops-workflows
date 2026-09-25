from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "policy" / "github-api-access-v1.json"
DOC_PATH = ROOT / "docs" / "GITHUB_API_ACCESS_V1.md"
AGENT_WORK_CYCLE_PATH = ROOT / "docs" / "AGENT_WORK_CYCLE_V1.md"
AGENTS_PATH = ROOT / "AGENTS.md"


class GitHubApiAccessPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.doc = DOC_PATH.read_text(encoding="utf-8")
        cls.agent_work_cycle = AGENT_WORK_CYCLE_PATH.read_text(encoding="utf-8")
        cls.agents = AGENTS_PATH.read_text(encoding="utf-8")

    def test_identity_and_authority_boundaries(self):
        self.assertEqual("rozkalns.github-api-access.v1", self.policy["schema"])
        self.assertEqual("ACTIVE_SHARED_GOVERNANCE", self.policy["status"])
        authority = self.policy["authority"]
        self.assertTrue(authority["github_is_canonical_mutable_state_source"])
        self.assertTrue(authority["repo_local_stricter_rules_win"])
        self.assertFalse(authority["changes_merge_authority"])
        self.assertFalse(authority["changes_live_authority"])
        self.assertFalse(authority["changes_deploy_authority"])
        self.assertFalse(authority["creates_mutation_retry_authority"])

    def test_serial_minimum_sufficient_and_event_driven_defaults(self):
        access = self.policy["access"]
        self.assertTrue(access["serial_by_default_per_repository_lane"])
        self.assertFalse(access["parallel_fanout_by_default"])
        self.assertTrue(access["minimum_sufficient_retrieval_required"])
        self.assertTrue(access["event_or_state_driven_continuation_preferred"])
        self.assertFalse(access["tight_polling_allowed"])
        self.assertTrue(access["honor_poll_interval_when_exposed"])

    def test_conditional_requests_are_capability_dependent(self):
        access = self.policy["access"]
        self.assertTrue(access["conditional_requests_when_transport_supports"])
        self.assertFalse(access["pretend_conditional_support_when_unavailable"])

    def test_request_budget_classes_are_stable(self):
        self.assertEqual(
            [
                "BOOTSTRAP_MINIMAL",
                "PR_REFRESH_COMPACT",
                "PR_FILES_ON_DEMAND",
                "FINAL_PREMERGE_COMPACT",
                "EXACT_MAIN_MINIMAL",
                "DEEP_AUDIT_EXPLICIT",
            ],
            self.policy["request_budget_classes"],
        )

    def test_graphql_is_bounded(self):
        graphql = self.policy["graphql"]
        self.assertTrue(graphql["optional"])
        self.assertTrue(graphql["use_only_when_total_request_cost_is_reduced"])
        self.assertEqual(1, graphql["connection_first_last_min"])
        self.assertEqual(100, graphql["connection_first_last_max"])
        self.assertEqual(500000, graphql["single_query_node_limit"])
        self.assertFalse(graphql["deep_unbounded_query_allowed"])

    def test_rate_limit_dispositions_are_machine_recognized(self):
        self.assertEqual(
            {
                "PRIMARY_RATE_LIMIT_EXHAUSTED",
                "SECONDARY_RATE_LIMIT_SUSPECTED",
                "RETRY_AFTER_REQUIRED",
                "RESET_WAIT_REQUIRED",
                "READ_BACKOFF_REQUIRED",
                "TRANSPORT_RATE_LIMIT_METADATA_UNAVAILABLE",
            },
            set(self.policy["rate_limit_dispositions"]),
        )

    def test_read_backoff_order_and_bounds(self):
        backoff = self.policy["read_backoff"]
        self.assertTrue(backoff["only_before_first_authorized_mutation"])
        self.assertTrue(backoff["retry_after_has_priority"])
        self.assertTrue(backoff["remaining_zero_wait_for_reset"])
        self.assertEqual(60, backoff["secondary_without_retry_after_min_wait_seconds"])
        self.assertTrue(backoff["repeated_secondary_uses_bounded_exponential_backoff"])
        self.assertFalse(backoff["busy_loop_allowed"])
        self.assertFalse(backoff["parallel_alternate_endpoint_probe_allowed"])
        self.assertTrue(backoff["must_obey_repo_local_stricter_attempt_limit"])

    def test_no_automatic_mutation_retry_authority(self):
        boundary = self.policy["mutation_boundary"]
        for key in (
            "automatic_duplicate_mutation_after_403",
            "automatic_duplicate_mutation_after_429",
            "automatic_duplicate_mutation_after_timeout",
            "automatic_duplicate_mutation_after_transport_error",
            "rate_limit_handling_may_create_mutation_authority",
        ):
            self.assertFalse(boundary[key])
        self.assertTrue(boundary["post_dispatch_uncertainty_fail_closed"])
        self.assertTrue(boundary["minimal_read_only_reconciliation_only"])

    def test_quota_evasion_is_forbidden(self):
        self.assertFalse(self.policy["access"]["quota_evasion_allowed"])
        self.assertEqual(
            {
                "TOKEN_ROTATION_FOR_QUOTA_EVASION",
                "ACCOUNT_ROTATION_FOR_QUOTA_EVASION",
                "IP_ROTATION_FOR_QUOTA_EVASION",
                "ENDPOINT_SWITCHING_TO_BYPASS_ENFORCEMENT",
            },
            set(self.policy["forbidden_evasion"]),
        )

    def test_human_contract_has_required_sections(self):
        for marker in (
            "## Core rules",
            "## Request-budget classes",
            "## Event-driven continuation",
            "## Rate-limit evidence classification",
            "## Pre-mutation read-only backoff",
            "## Mutation boundary",
            "## GraphQL and REST bounds",
            "## Compatibility and authority",
        ):
            self.assertIn(marker, self.doc)

    def test_active_work_cycle_points_to_contract(self):
        marker = "docs/GITHUB_API_ACCESS_V1.md"
        self.assertIn(marker, self.agent_work_cycle)
        self.assertIn(marker, self.agents)


if __name__ == "__main__":
    unittest.main()
