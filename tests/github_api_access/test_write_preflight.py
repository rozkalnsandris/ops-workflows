from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from write_preflight_model import (
    ALREADY_SATISFIED,
    AUTHORITY_DRIFT,
    CAPABILITY_UNAVAILABLE,
    CONFLICT,
    DUPLICATE_CONFLICT,
    DUPLICATE_EXACT,
    ELIGIBLE,
    INVALID_HEAD_BASE,
    preflight_branch_create,
    preflight_durable_object,
    preflight_metadata_update,
    preflight_pr_create,
)

PARENT_POLICY = ROOT / "policy" / "github-api-access-v1.json"
EXTENSION_POLICY = ROOT / "policy" / "github-api-access-write-preflight-v1.json"
DOC = ROOT / "docs" / "WRITE_PREFLIGHT_COMPACT_V1.md"


class WritePreflightCompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = json.loads(PARENT_POLICY.read_text(encoding="utf-8"))
        cls.extension = json.loads(EXTENSION_POLICY.read_text(encoding="utf-8"))
        cls.doc = DOC.read_text(encoding="utf-8")

    def test_extension_is_bound_to_active_parent_contract(self):
        self.assertEqual("rozkalns.github-api-access.v1", self.parent["schema"])
        self.assertEqual(
            "rozkalns.github-api-access.v1",
            self.extension["parent_contract"]["schema"],
        )
        self.assertEqual("WRITE_PREFLIGHT_COMPACT", self.extension["budget_class"])
        self.assertEqual(122, self.extension["tracking_issue"])

    def test_preflight_never_creates_authority_or_consumes_before_dispatch(self):
        authority = self.extension["authority"]
        self.assertFalse(authority["preflight_is_authorization"])
        self.assertFalse(authority["creates_source_authority"])
        self.assertFalse(authority["creates_merge_authority"])
        self.assertFalse(authority["creates_live_or_deploy_authority"])
        self.assertFalse(authority["creates_retry_rollback_cleanup_authority"])
        self.assertFalse(authority["read_only_noop_or_rejection_consumes_mutation_authority"])

    def test_branch_absent_is_eligible(self):
        result = preflight_branch_create(intended_sha="abc", existing_sha=None)
        self.assertEqual((ELIGIBLE, True), (result.disposition, result.dispatch_allowed))

    def test_branch_exact_sha_is_idempotent_noop(self):
        result = preflight_branch_create(intended_sha="abc", existing_sha="abc")
        self.assertEqual(
            (ALREADY_SATISFIED, False),
            (result.disposition, result.dispatch_allowed),
        )

    def test_branch_conflicting_sha_stops_without_recovery_authority(self):
        result = preflight_branch_create(intended_sha="abc", existing_sha="def")
        self.assertEqual((CONFLICT, False), (result.disposition, result.dispatch_allowed))
        profile = self.extension["profiles"]["CREATE_BRANCH_REF"]
        self.assertFalse(profile["force_update_allowed"])
        self.assertFalse(profile["delete_recreate_allowed"])
        self.assertFalse(profile["alternate_branch_allowed"])

    def test_exact_existing_pr_reuses_canonical_identity(self):
        result = preflight_pr_create(
            base_exists=True,
            head_exists=True,
            has_eligible_diff=True,
            existing_pr={"base": "main", "head": "topic", "identity": 42},
            intended_base="main",
            intended_head="topic",
        )
        self.assertEqual(DUPLICATE_EXACT, result.disposition)
        self.assertFalse(result.dispatch_allowed)
        self.assertEqual("42", result.canonical_identity)

    def test_pr_invalid_head_base_or_no_diff_rejects_before_dispatch(self):
        missing_head = preflight_pr_create(
            base_exists=True,
            head_exists=False,
            has_eligible_diff=True,
            intended_base="main",
            intended_head="topic",
        )
        no_diff = preflight_pr_create(
            base_exists=True,
            head_exists=True,
            has_eligible_diff=False,
            intended_base="main",
            intended_head="topic",
        )
        self.assertEqual(INVALID_HEAD_BASE, missing_head.disposition)
        self.assertEqual(INVALID_HEAD_BASE, no_diff.disposition)
        self.assertFalse(missing_head.dispatch_allowed)
        self.assertFalse(no_diff.dispatch_allowed)

    def test_conflicting_existing_pr_rejects(self):
        result = preflight_pr_create(
            base_exists=True,
            head_exists=True,
            has_eligible_diff=True,
            existing_pr={"base": "release", "head": "topic", "identity": 42},
            intended_base="main",
            intended_head="topic",
        )
        self.assertEqual(DUPLICATE_CONFLICT, result.disposition)
        self.assertFalse(result.dispatch_allowed)

    def test_exact_durable_identity_reconciles_and_collision_stops(self):
        exact = preflight_durable_object(
            object_found=True,
            protected_payload_matches=True,
            canonical_identity="issue:99",
        )
        collision = preflight_durable_object(
            object_found=True,
            protected_payload_matches=False,
            canonical_identity="issue:99",
        )
        self.assertEqual(DUPLICATE_EXACT, exact.disposition)
        self.assertEqual("issue:99", exact.canonical_identity)
        self.assertEqual(DUPLICATE_CONFLICT, collision.disposition)
        self.assertFalse(exact.dispatch_allowed)
        self.assertFalse(collision.dispatch_allowed)

    def test_metadata_already_intended_is_noop_and_safe_delta_is_eligible(self):
        noop = preflight_metadata_update(
            current={"state": "open", "title": "A"},
            intended={"state": "open"},
        )
        delta = preflight_metadata_update(
            current={"state": "open"},
            intended={"state": "closed"},
        )
        self.assertEqual(ALREADY_SATISFIED, noop.disposition)
        self.assertFalse(noop.dispatch_allowed)
        self.assertEqual(ELIGIBLE, delta.disposition)
        self.assertTrue(delta.dispatch_allowed)

    def test_authority_drift_rejects_before_dispatch(self):
        result = preflight_branch_create(
            intended_sha="abc",
            existing_sha=None,
            authority_current=False,
        )
        self.assertEqual(AUTHORITY_DRIFT, result.disposition)
        self.assertFalse(result.dispatch_allowed)

    def test_missing_capability_fails_closed_without_broad_scan(self):
        result = preflight_branch_create(
            intended_sha="abc",
            existing_sha=None,
            targeted_lookup_available=False,
        )
        self.assertEqual(CAPABILITY_UNAVAILABLE, result.disposition)
        self.assertFalse(result.dispatch_allowed)
        access = self.extension["access"]
        self.assertFalse(access["unrelated_repo_scan_allowed"])
        self.assertFalse(
            access["alternate_tool_or_endpoint_for_broader_duplicate_search_allowed"]
        )

    def test_post_dispatch_ambiguity_still_uses_parent_mutation_boundary(self):
        post = self.extension["post_dispatch"]
        parent_boundary = self.parent["mutation_boundary"]
        self.assertTrue(post["parent_mutation_boundary_required"])
        self.assertFalse(post["rerun_preflight_to_create_retry_authority"])
        self.assertFalse(post["automatic_duplicate_mutation_allowed"])
        self.assertTrue(parent_boundary["post_dispatch_uncertainty_fail_closed"])
        self.assertFalse(parent_boundary["automatic_duplicate_mutation_after_429"])
        self.assertFalse(parent_boundary["automatic_duplicate_mutation_after_timeout"])

    def test_merge_remains_on_final_premerge_compact(self):
        merge = self.extension["profiles"]["MERGE"]
        self.assertFalse(merge["handled_by_write_preflight_compact"])
        self.assertEqual("FINAL_PREMERGE_COMPACT", merge["parent_budget_class"])
        self.assertEqual(
            "FINAL_PREMERGE_COMPACT",
            self.parent["mutation_boundary"]["final_pre_mutation_budget_class"],
        )

    def test_doc_is_explicitly_parent_appendix_and_has_profiles(self):
        for marker in (
            "normative appendix of `GITHUB_API_ACCESS_V1`",
            "## Stable dispositions",
            "### Create branch/ref",
            "### Create pull request",
            "### Durable issue/controller/receipt object",
            "### Durable comment/receipt",
            "### Update issue/PR metadata",
            "### Merge",
            "## Authority and dispatch boundary",
            "## Capability honesty",
        ):
            self.assertIn(marker, self.doc)


if __name__ == "__main__":
    unittest.main()
