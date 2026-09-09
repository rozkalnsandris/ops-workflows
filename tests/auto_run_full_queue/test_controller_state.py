from __future__ import annotations

import copy
import importlib.util
import json
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_auto_run_full_queue_state.py"

spec = importlib.util.spec_from_file_location("queue_state", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def queue_id() -> str:
    return str(uuid.UUID("123e4567-e89b-42d3-a456-426614174000"))


def evidence(pr_number: int, marker: str) -> dict:
    char = marker.lower()
    return {
        "pr_number": pr_number,
        "merged_head_sha": char * 40,
        "exact_main_sha": ("f" if char != "f" else "e") * 40,
        "exact_main_ci": "PASS",
    }


class QueueControllerStateTests(unittest.TestCase):
    def ready(self) -> dict:
        return mod.make_ready("rozkalnsandris/example", [101, 102, 103], queue_id())

    def test_ready_snapshot_is_valid_and_has_no_active_issue(self):
        snapshot = self.ready()
        self.assertEqual(mod.validate_snapshot(snapshot), [])
        self.assertEqual(snapshot["state"], "READY")
        self.assertIsNone(snapshot["active_issue"])
        self.assertEqual([item["state"] for item in snapshot["items"]], ["PENDING"] * 3)

    def test_activate_selects_only_first_frozen_issue(self):
        snapshot = mod.activate(self.ready())
        self.assertEqual(snapshot["cursor"], 0)
        self.assertEqual(snapshot["active_issue"], 101)
        self.assertEqual([item["state"] for item in snapshot["items"]], ["ACTIVE", "PENDING", "PENDING"])

    def test_advance_moves_exactly_one_and_preserves_terminal_evidence(self):
        active = mod.activate(self.ready())
        advanced = mod.advance_after_source_complete(active, evidence(201, "a"))
        self.assertEqual(advanced["cursor"], 1)
        self.assertEqual(advanced["active_issue"], 102)
        self.assertEqual(
            [item["state"] for item in advanced["items"]],
            ["SOURCE_COMPLETE", "ACTIVE", "PENDING"],
        )
        self.assertEqual(advanced["items"][0]["terminal_evidence"], evidence(201, "a"))

    def test_final_advance_enters_queue_source_complete(self):
        snapshot = mod.activate(self.ready())
        snapshot = mod.advance_after_source_complete(snapshot, evidence(201, "a"))
        snapshot = mod.advance_after_source_complete(snapshot, evidence(202, "b"))
        snapshot = mod.advance_after_source_complete(snapshot, evidence(203, "c"))
        self.assertEqual(snapshot["state"], "QUEUE_SOURCE_COMPLETE")
        self.assertEqual(snapshot["cursor"], 3)
        self.assertIsNone(snapshot["active_issue"])
        self.assertTrue(all(item["state"] == "SOURCE_COMPLETE" for item in snapshot["items"]))

    def test_pause_resume_preserves_cursor_order_and_active_issue(self):
        active = mod.advance_after_source_complete(mod.activate(self.ready()), evidence(201, "a"))
        paused = mod.pause(active)
        resumed = mod.resume(paused)
        self.assertEqual(paused["state"], "PAUSED")
        self.assertEqual(resumed["state"], "ACTIVE")
        self.assertEqual(resumed["cursor"], 1)
        self.assertEqual(resumed["active_issue"], 102)
        self.assertEqual(resumed["frozen_issues"], [101, 102, 103])

    def test_stop_does_not_advance_or_mark_source_complete(self):
        active = mod.advance_after_source_complete(mod.activate(self.ready()), evidence(201, "a"))
        stopped = mod.stop(active)
        self.assertEqual(stopped["state"], "STOPPED")
        self.assertEqual(stopped["cursor"], 1)
        self.assertEqual(stopped["active_issue"], 102)
        self.assertEqual(
            [item["state"] for item in stopped["items"]],
            ["SOURCE_COMPLETE", "STOPPED", "PENDING"],
        )
        self.assertIsNone(stopped["items"][1]["terminal_evidence"])

    def test_duplicate_or_reordered_frozen_scope_fails_closed(self):
        with self.assertRaises(ValueError):
            mod.make_ready("rozkalnsandris/example", [101, 101], queue_id())

        snapshot = self.ready()
        snapshot["frozen_issues"] = [102, 101, 103]
        self.assertTrue(any("preserve frozen order" in error for error in mod.validate_snapshot(snapshot)))

    def test_two_active_items_fail_closed(self):
        snapshot = mod.activate(self.ready())
        snapshot["items"][1]["state"] = "ACTIVE"
        self.assertTrue(any("item state mismatch" in error for error in mod.validate_snapshot(snapshot)))

    def test_cursor_skip_attempt_fails_closed(self):
        snapshot = mod.activate(self.ready())
        snapshot["cursor"] = 2
        snapshot["active_issue"] = 103
        snapshot["items"][0]["state"] = "PENDING"
        snapshot["items"][2]["state"] = "ACTIVE"
        errors = mod.validate_snapshot(snapshot)
        self.assertTrue(any("expected SOURCE_COMPLETE" in error for error in errors))

    def test_advance_requires_complete_exact_main_evidence(self):
        snapshot = mod.activate(self.ready())
        bad = evidence(201, "a")
        bad["exact_main_ci"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "exact_main_ci must equal PASS"):
            mod.advance_after_source_complete(snapshot, bad)

        bad = evidence(201, "a")
        bad["exact_main_sha"] = "A" * 40
        with self.assertRaisesRegex(ValueError, "lowercase 40-hex"):
            mod.advance_after_source_complete(snapshot, bad)

    def test_stopped_queue_cannot_auto_resume_or_advance(self):
        stopped = mod.stop(mod.activate(self.ready()))
        with self.assertRaises(ValueError):
            mod.resume(stopped)
        with self.assertRaises(ValueError):
            mod.advance_after_source_complete(stopped, evidence(201, "a"))

    def test_schema_matches_validator_surface(self):
        schema = json.loads(
            (ROOT / "policy" / "schemas" / "auto-run-full-queue-controller-state-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), mod.TOP_LEVEL_FIELDS)
        self.assertEqual(set(schema["properties"]), mod.TOP_LEVEL_FIELDS)
        self.assertEqual(schema["properties"]["schema"]["const"], mod.SCHEMA)
        self.assertEqual(set(schema["properties"]["state"]["enum"]), mod.QUEUE_STATES)
        self.assertEqual(set(schema["$defs"]["item"]["properties"]["state"]["enum"]), mod.ITEM_STATES)

    def test_a2_contract_is_source_only_and_non_authoritative(self):
        policy = json.loads(
            (ROOT / "policy" / "auto-run-full-queue-controller-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(policy["status"], "A2_SHARED_CONTROLLER_STATE_CONTRACT_NOT_ACTIVE")
        self.assertTrue(policy["source_policy_only"])
        self.assertFalse(policy["activation"]["executor_active"])
        self.assertFalse(policy["activation"]["queue_command_active"])
        self.assertFalse(policy["activation"]["controller_snapshot_is_authority"])
        self.assertFalse(policy["authorization"]["a2_grants_queue_wide_source_authority"])
        self.assertFalse(policy["authorization"]["a2_grants_queue_wide_merge_authority"])
        self.assertFalse(policy["authorization"]["queue_authorizes_live"])
        self.assertTrue(policy["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"])

    def test_a1_compatibility_contract_remains_inactive(self):
        policy = json.loads((ROOT / "policy" / "auto-run-full-queue-v1.json").read_text(encoding="utf-8"))
        self.assertFalse(policy["activation"]["command_active"])
        self.assertTrue(policy["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"])
        self.assertFalse(policy["authorization"]["a1_grants_queue_wide_source_authority"])
        self.assertFalse(policy["authorization"]["a1_grants_queue_wide_merge_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
