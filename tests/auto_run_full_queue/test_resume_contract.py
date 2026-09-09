from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_auto_run_full_queue_resume.py"

spec = importlib.util.spec_from_file_location("queue_resume", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def github_signal(**overrides) -> dict:
    signal = {
        "schema": mod.SCHEMA,
        "repository": "rozkalnsandris/example",
        "repository_id": 123456,
        "source": "GITHUB_EVENT",
        "event_name": "pull_request",
        "event_action": "synchronize",
        "delivery_id": "delivery-guid-1",
        "observed_at": "2026-09-09T19:30:00+02:00",
        "target_issue_number": 10,
        "target_pr_number": 20,
    }
    signal.update(overrides)
    return signal


def watchdog_signal() -> dict:
    return github_signal(
        source="WATCHDOG",
        event_name="watchdog",
        event_action=None,
        delivery_id=None,
        target_issue_number=None,
        target_pr_number=None,
    )


def manual_signal() -> dict:
    return github_signal(
        source="MANUAL_CONTINUATION",
        event_name="manual_continuation",
        event_action=None,
        delivery_id=None,
        target_issue_number=None,
        target_pr_number=None,
    )


class QueueResumeContractTests(unittest.TestCase):
    def test_valid_signal_sources_pass(self):
        self.assertEqual(mod.validate_signal(github_signal()), [])
        self.assertEqual(mod.validate_signal(watchdog_signal()), [])
        self.assertEqual(mod.validate_signal(manual_signal()), [])

    def test_signal_cannot_carry_authority_fields(self):
        signal = github_signal()
        signal["merge_authority"] = True
        self.assertEqual(mod.validate_signal(signal), ["signal keys mismatch"])

    def test_unknown_github_event_fails_closed(self):
        signal = github_signal(event_name="deployment")
        self.assertIn("GitHub event is not allowlisted", mod.validate_signal(signal))

    def test_watchdog_has_no_event_payload_or_target_hints(self):
        signal = watchdog_signal()
        signal["delivery_id"] = "not-allowed"
        signal["target_issue_number"] = 10
        errors = mod.validate_signal(signal)
        self.assertIn("watchdog source must not carry delivery_id", errors)
        self.assertIn("watchdog source must not carry target issue or PR", errors)

    def test_observed_at_requires_timezone(self):
        signal = github_signal(observed_at="2026-09-09T19:30:00")
        self.assertIn(
            "observed_at must be an offset-aware ISO-8601 datetime",
            mod.validate_signal(signal),
        )

    def test_delivery_guid_is_best_effort_dedupe_only(self):
        signal = github_signal(delivery_id="same-guid")
        self.assertEqual(mod.delivery_dedupe_key(signal), "github-delivery:same-guid")

        no_guid = github_signal(delivery_id=None)
        self.assertIsNone(mod.delivery_dedupe_key(no_guid))
        self.assertEqual(mod.validate_signal(no_guid), [])

    def test_repository_identity_filters_wake(self):
        signal = github_signal()
        self.assertTrue(
            mod.event_may_wake(
                signal,
                expected_repository="rozkalnsandris/example",
                expected_repository_id=123456,
            )
        )
        self.assertFalse(
            mod.event_may_wake(
                signal,
                expected_repository="rozkalnsandris/other",
                expected_repository_id=123456,
            )
        )
        self.assertFalse(
            mod.event_may_wake(
                signal,
                expected_repository="rozkalnsandris/example",
                expected_repository_id=999,
            )
        )

    def test_active_and_paused_resume_only_after_refresh(self):
        for state in ("ACTIVE", "PAUSED"):
            result = mod.decide_after_canonical_refresh(
                queue_state=state,
                signal_relevant=True,
                canonical_refresh_complete=True,
                authority_valid=True,
                scope_rules_main_valid=True,
                owner_gate_required=False,
            )
            self.assertEqual(result, "RESUME_ACTIVE_ITEM")

    def test_ready_signal_never_auto_activates(self):
        result = mod.decide_after_canonical_refresh(
            queue_state="READY",
            signal_relevant=True,
            canonical_refresh_complete=True,
            authority_valid=True,
            scope_rules_main_valid=True,
            owner_gate_required=False,
        )
        self.assertEqual(result, "NOOP_NOT_ACTIVATED")

    def test_stopped_signal_never_auto_resumes(self):
        result = mod.decide_after_canonical_refresh(
            queue_state="STOPPED",
            signal_relevant=True,
            canonical_refresh_complete=True,
            authority_valid=True,
            scope_rules_main_valid=True,
            owner_gate_required=False,
        )
        self.assertEqual(result, "STOPPED_NO_AUTO_RESUME")

    def test_queue_complete_wake_is_read_only_reconcile(self):
        result = mod.decide_after_canonical_refresh(
            queue_state="QUEUE_SOURCE_COMPLETE",
            signal_relevant=True,
            canonical_refresh_complete=True,
            authority_valid=True,
            scope_rules_main_valid=True,
            owner_gate_required=False,
        )
        self.assertEqual(result, "READ_ONLY_FINAL_RECONCILE")

    def test_owner_gate_cannot_be_bypassed(self):
        result = mod.decide_after_canonical_refresh(
            queue_state="ACTIVE",
            signal_relevant=True,
            canonical_refresh_complete=True,
            authority_valid=True,
            scope_rules_main_valid=True,
            owner_gate_required=True,
        )
        self.assertEqual(result, "OWNER_GATE_NO_AUTO_RESUME")

    def test_incomplete_or_drifted_refresh_stops(self):
        self.assertEqual(
            mod.decide_after_canonical_refresh(
                queue_state="ACTIVE",
                signal_relevant=True,
                canonical_refresh_complete=False,
                authority_valid=True,
                scope_rules_main_valid=True,
                owner_gate_required=False,
            ),
            "STOP_CANONICAL_REFRESH_INCOMPLETE",
        )
        self.assertEqual(
            mod.decide_after_canonical_refresh(
                queue_state="ACTIVE",
                signal_relevant=True,
                canonical_refresh_complete=True,
                authority_valid=False,
                scope_rules_main_valid=True,
                owner_gate_required=False,
            ),
            "STOP_REVALIDATION_FAILED",
        )
        self.assertEqual(
            mod.decide_after_canonical_refresh(
                queue_state="ACTIVE",
                signal_relevant=True,
                canonical_refresh_complete=True,
                authority_valid=True,
                scope_rules_main_valid=False,
                owner_gate_required=False,
            ),
            "STOP_REVALIDATION_FAILED",
        )

    def test_irrelevant_and_duplicate_signals_do_not_advance_state(self):
        kwargs = dict(
            queue_state="ACTIVE",
            signal_relevant=True,
            canonical_refresh_complete=True,
            authority_valid=True,
            scope_rules_main_valid=True,
            owner_gate_required=False,
        )
        first = mod.decide_after_canonical_refresh(**kwargs)
        second = mod.decide_after_canonical_refresh(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first, "RESUME_ACTIVE_ITEM")

        kwargs["signal_relevant"] = False
        self.assertEqual(mod.decide_after_canonical_refresh(**kwargs), "IGNORE")

    def test_schema_and_validator_fields_match(self):
        schema = json.loads(
            (
                ROOT
                / "policy"
                / "schemas"
                / "auto-run-full-queue-resume-signal-v1.schema.json"
            ).read_text()
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), mod.SIGNAL_FIELDS)
        self.assertEqual(set(schema["properties"]), mod.SIGNAL_FIELDS)
        self.assertEqual(schema["properties"]["schema"]["const"], mod.SCHEMA)
        self.assertEqual(set(schema["properties"]["source"]["enum"]), mod.SOURCES)

    def test_machine_policy_preserves_a4_non_activation_and_legacy_mode(self):
        policy = json.loads(
            (ROOT / "policy" / "auto-run-full-queue-resume-v1.json").read_text()
        )
        self.assertEqual(policy["status"], "A4_SHARED_RESUME_CONTRACT_NOT_ACTIVE")
        self.assertTrue(policy["source_policy_only"])
        self.assertFalse(policy["activation"]["consumer_event_resume_active"])
        self.assertFalse(policy["activation"]["consumer_watchdog_active"])
        self.assertFalse(policy["activation"]["consumer_auto_migration"])
        self.assertTrue(
            policy["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"]
        )
        self.assertFalse(policy["canonical_state"]["event_payload_is_authority"])
        self.assertFalse(policy["canonical_state"]["watchdog_tick_is_authority"])
        self.assertTrue(policy["canonical_state"]["controller_must_refresh_before_action"])
        self.assertTrue(policy["canonical_state"]["event_never_directly_advances_cursor"])
        self.assertTrue(policy["owner_gate_behavior"]["queue_resume_never_grants_live"])

    def test_prior_a1_a2_a3_activation_boundaries_remain_unchanged(self):
        a1 = json.loads((ROOT / "policy" / "auto-run-full-queue-v1.json").read_text())
        a2 = json.loads(
            (ROOT / "policy" / "auto-run-full-queue-controller-v1.json").read_text()
        )
        a3 = json.loads(
            (ROOT / "policy" / "auto-run-full-queue-authorization-v1.json").read_text()
        )
        self.assertEqual(a1["status"], "A1_SHARED_SOURCE_POLICY_DESIGN_NOT_ACTIVE")
        self.assertEqual(a2["status"], "A2_SHARED_CONTROLLER_STATE_CONTRACT_NOT_ACTIVE")
        self.assertEqual(a3["status"], "A3_SHARED_BATCH_AUTHORIZATION_CONTRACT_NOT_ACTIVE")
        self.assertTrue(
            a1["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"]
        )
        self.assertTrue(
            a2["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"]
        )
        self.assertTrue(
            a3["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"]
        )

    def test_normative_doc_states_trigger_is_not_authority(self):
        text = (ROOT / "docs" / "AUTO_RUN_FULL_QUEUE_RESUME_V1.md").read_text().lower()
        self.assertIn("a trigger is a notification, not a state transition", text)
        self.assertIn("no_auto_resume", text)
        self.assertIn("read_only_final_reconciliation_only", text)
        self.assertIn("queue resume is never live authority", text)
        self.assertIn("a4 does not activate queue mode", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
