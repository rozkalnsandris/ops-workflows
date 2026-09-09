import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_simple_live_ready.py"
SPEC = importlib.util.spec_from_file_location("validate_simple_live_ready", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_payload():
    return {
        "schema": "rozkalns.simple-live-ready.v1",
        "classification": "OWNER_LIVE_REQUIRED",
        "queue_id": "01234567-89ab-4cde-8fab-0123456789ab",
        "source_repository": "rozkalnsandris/example",
        "source_sha": "1" * 40,
        "target_alias": "example-production",
        "operation_id": "example.application-deploy.v1",
        "operation_contract_digest_sha256": "2" * 64,
        "consumer_rules_digest_sha256": "3" * 64,
        "shared_contract_sha": "4" * 40,
        "expected_baseline": {"kind": "EXACT_SHA", "value": "5" * 40},
        "read_only_preflight_digest_sha256": "6" * 64,
        "allowed_mutation_classes": ["APPLICATION_DEPLOY"],
        "maximum_total_mutations": 2,
        "exclusions": ["database writes", "credential changes", "permission changes"],
    }


class SimpleLiveReadyTests(unittest.TestCase):
    def test_valid_payload_and_binding_are_deterministic(self):
        payload = valid_payload()
        MODULE.validate_ready(payload)
        first = MODULE.binding_sha256(payload)
        second = MODULE.binding_sha256(copy.deepcopy(payload))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertEqual(MODULE.owner_command(payload), f"LIVE {first}")

    def test_unknown_field_fails_closed(self):
        payload = valid_payload()
        payload["shell"] = "rm -rf /"
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_ready(payload)

    def test_changed_target_changes_binding(self):
        payload = valid_payload()
        changed = copy.deepcopy(payload)
        changed["target_alias"] = "other-production"
        self.assertNotEqual(MODULE.binding_sha256(payload), MODULE.binding_sha256(changed))

    def test_changed_baseline_changes_binding(self):
        payload = valid_payload()
        changed = copy.deepcopy(payload)
        changed["expected_baseline"]["value"] = "7" * 40
        self.assertNotEqual(MODULE.binding_sha256(payload), MODULE.binding_sha256(changed))

    def test_unavailable_baseline_requires_reason(self):
        payload = valid_payload()
        payload["expected_baseline"] = {"kind": "UNAVAILABLE", "value": "NOT_EXPOSED"}
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_ready(payload)
        payload["expected_baseline"]["unavailable_reason"] = "provider exposes no stable pre-mutation identity"
        MODULE.validate_ready(payload)

    def test_unavailable_reason_for_known_baseline_is_rejected(self):
        payload = valid_payload()
        payload["expected_baseline"]["unavailable_reason"] = "not allowed here"
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_ready(payload)

    def test_duplicate_mutation_classes_fail(self):
        payload = valid_payload()
        payload["allowed_mutation_classes"] = ["APPLICATION_DEPLOY", "APPLICATION_DEPLOY"]
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_ready(payload)

    def test_duplicate_exclusions_fail(self):
        payload = valid_payload()
        payload["exclusions"] = ["database writes", "database writes"]
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_ready(payload)

    def test_no_live_required_finishes_without_owner_gate(self):
        result = MODULE.final_disposition(
            queue_state="QUEUE_SOURCE_COMPLETE",
            classification="NO_LIVE_REQUIRED",
            exact_main_matches=True,
            exact_main_ci_pass=True,
            read_only_preflight_complete=True,
            fixed_operation_proven=True,
        )
        self.assertEqual(result, "DONE_NO_LIVE")

    def test_live_ready_requires_all_source_and_preflight_gates(self):
        result = MODULE.final_disposition(
            queue_state="QUEUE_SOURCE_COMPLETE",
            classification="OWNER_LIVE_REQUIRED",
            exact_main_matches=True,
            exact_main_ci_pass=True,
            read_only_preflight_complete=True,
            fixed_operation_proven=True,
        )
        self.assertEqual(result, "OWNER_LIVE_REQUIRED")

        blocked = MODULE.final_disposition(
            queue_state="ACTIVE",
            classification="OWNER_LIVE_REQUIRED",
            exact_main_matches=True,
            exact_main_ci_pass=True,
            read_only_preflight_complete=True,
            fixed_operation_proven=True,
        )
        self.assertEqual(blocked, "BLOCKED_SOURCE_NOT_COMPLETE")

    def test_ambiguity_blocks(self):
        result = MODULE.final_disposition(
            queue_state="QUEUE_SOURCE_COMPLETE",
            classification="OWNER_LIVE_REQUIRED",
            exact_main_matches=True,
            exact_main_ci_pass=True,
            read_only_preflight_complete=True,
            fixed_operation_proven=True,
            ambiguity=True,
        )
        self.assertEqual(result, "BLOCKED_AMBIGUOUS")

    def test_binding_must_be_identical_after_refresh(self):
        payload = valid_payload()
        approved = MODULE.binding_sha256(payload)
        self.assertTrue(MODULE.binding_still_current(payload, approved, copy.deepcopy(payload)))
        changed = copy.deepcopy(payload)
        changed["source_sha"] = "8" * 40
        self.assertFalse(MODULE.binding_still_current(payload, approved, changed))

    def test_shared_policy_keeps_a5_inactive_and_separate_from_live_auth(self):
        policy = json.loads((ROOT / "policy" / "simple-live-v1.json").read_text())
        self.assertEqual(policy["status"], "A5_SHARED_SIMPLE_LIVE_CONTRACT_NOT_ACTIVE")
        self.assertTrue(policy["source_policy_only"])
        self.assertFalse(policy["activation"]["consumer_mode_active"])
        self.assertFalse(policy["activation"]["queue_authorizes_live"])
        self.assertFalse(policy["activation"]["ready_envelope_is_authority"])
        self.assertTrue(policy["activation"]["fresh_explicit_owner_live_decision_required"])
        self.assertFalse(policy["activation"]["may_infer_live_from_merge_start_continue_history_or_ready_state"])
        self.assertFalse(policy["execution"]["ops_workflows_executes_production"])
        self.assertTrue(policy["deferred_trusted_executor"]["existing_live_auth_v1_required_for_deferred_rpi5_execution"])
        self.assertFalse(policy["deferred_trusted_executor"]["simple_live_replaces_live_auth_v1_author_identity_ttl_or_replay_rules"])
        self.assertFalse(policy["deferred_trusted_executor"]["live_auth_materialization_may_occur_before_owner_live_decision"])
        self.assertFalse(policy["auto_live_compatibility"]["auto_live_v1_is_automatically_disabled"])
        self.assertFalse(policy["auto_live_compatibility"]["double_execution_paths_for_same_operation_allowed"])

    def test_docs_preserve_fixed_operation_and_failure_boundaries(self):
        text = (ROOT / "docs" / "SIMPLE_LIVE_V1.md").read_text()
        required = [
            "LIVE <binding_sha256>",
            "Ready envelope is evidence, not authority",
            "fixed reviewed operation identity",
            "authorization is consumed when the first state-changing operation starts",
            "existing LIVE-AUTH v1",
            "does not disable or silently replace existing Auto-Live v1 consumers",
            "D1 or other storage mutation is not implicitly included",
            "ops-workflows",
            "RPi5_main",
        ]
        for needle in required:
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
