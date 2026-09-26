from __future__ import annotations

import copy
import importlib.util
import json
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_auto_run_full_single_issue_state.py"

spec = importlib.util.spec_from_file_location("single_issue_state", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

RUN_ID = str(uuid.UUID("123e4567-e89b-42d3-a456-426614174000"))
SCOPE = "a" * 64
REPO = "rozkalnsandris/example"

def completion():
    return {"exact_main_sha": "b" * 40, "receipt_ref": "issue:123#completion:v2"}

class SingleIssueStateNormalizationTests(unittest.TestCase):
    def planned(self):
        return mod.make_planned(REPO, 123, RUN_ID, SCOPE)

    def active_pair(self):
        run = self.planned()
        ctl = mod.activate_controller(mod.make_idle_controller(REPO), run, "activate:1")
        run = mod.transition_run(
            run, ctl, expected_revision=0, transition_id="phase:1",
            next_phase="ACTIVE_SOURCE", branch="auto-full/123",
        )
        ctl = mod.apply_transition_to_controller(ctl, run, "phase:1")
        return run, ctl

    def test_schemas_are_closed_and_minimal_controller_has_no_duplicated_work_state(self):
        run_schema = json.loads((ROOT / "policy/schemas/auto-run-full-single-issue-run-state-v2.schema.json").read_text())
        ctl_schema = json.loads((ROOT / "policy/schemas/auto-run-full-single-issue-controller-v2.schema.json").read_text())
        self.assertFalse(run_schema["additionalProperties"])
        self.assertFalse(ctl_schema["additionalProperties"])
        self.assertEqual(set(run_schema["required"]), mod.RUN_FIELDS)
        self.assertEqual(set(ctl_schema["required"]), mod.CONTROLLER_FIELDS)
        for forbidden in ("phase", "branch", "pr_number", "correction_count", "stop_reason", "owner_gate", "completion"):
            self.assertNotIn(forbidden, ctl_schema["properties"])

    def test_idle_to_active_binds_exactly_one_issue_and_run(self):
        run = self.planned()
        ctl = mod.activate_controller(mod.make_idle_controller(REPO), run, "activate:1")
        self.assertEqual(ctl["state"], "ACTIVE")
        self.assertEqual(ctl["active_issue"], 123)
        self.assertEqual(ctl["active_run_id"], RUN_ID)
        self.assertEqual(ctl["active_run_digest_sha256"], mod.active_run_digest(run))

    def test_second_issue_cannot_activate_while_controller_is_active(self):
        run = self.planned()
        ctl = mod.activate_controller(mod.make_idle_controller(REPO), run, "activate:1")
        other = mod.make_planned(REPO, 124, str(uuid.UUID("123e4567-e89b-42d3-a456-426614174001")), "c"*64)
        with self.assertRaisesRegex(ValueError, "already ACTIVE"):
            mod.activate_controller(ctl, other, "activate:2")

    def test_exact_activation_replay_is_idempotent_but_collision_stops(self):
        run = self.planned()
        ctl = mod.activate_controller(mod.make_idle_controller(REPO), run, "activate:1")
        self.assertEqual(mod.activate_controller(ctl, run, "activate:1"), ctl)
        with self.assertRaises(ValueError):
            mod.activate_controller(ctl, run, "different-transition")

    def test_exact_run_transition_replay_is_idempotent_but_content_collision_stops(self):
        run, ctl = self.active_pair()
        advanced = mod.transition_run(
            run, ctl, expected_revision=1, transition_id="phase:2",
            next_phase="PR_OPEN", pr_number=77,
        )
        advanced_ctl = mod.apply_transition_to_controller(ctl, advanced, "phase:2")
        replay = mod.transition_run(
            advanced, advanced_ctl, expected_revision=1, transition_id="phase:2",
            next_phase="PR_OPEN", pr_number=77,
        )
        self.assertEqual(replay, advanced)
        with self.assertRaisesRegex(ValueError, "content collision"):
            mod.transition_run(
                advanced, advanced_ctl, expected_revision=1, transition_id="phase:2",
                next_phase="PR_OPEN", pr_number=78,
            )

    def test_state_machine_reaches_ready_and_done(self):
        run, ctl = self.active_pair()
        run = mod.transition_run(run, ctl, expected_revision=1, transition_id="phase:2", next_phase="PR_OPEN", pr_number=77)
        ctl = mod.apply_transition_to_controller(ctl, run, "phase:2")
        run = mod.transition_run(run, ctl, expected_revision=2, transition_id="phase:3", next_phase="WAITING_CI")
        ctl = mod.apply_transition_to_controller(ctl, run, "phase:3")
        run = mod.transition_run(run, ctl, expected_revision=3, transition_id="phase:4", next_phase="READY", owner_gate="MERGE")
        ctl = mod.apply_transition_to_controller(ctl, run, "phase:4")
        run = mod.transition_run(run, ctl, expected_revision=4, transition_id="phase:5", next_phase="DONE", completion=completion())
        ctl = mod.apply_transition_to_controller(ctl, run, "phase:5")
        self.assertEqual(run["phase"], "DONE")
        self.assertEqual(run["revision"], 5)
        self.assertIsNone(run["owner_gate"])
        released = mod.release_completed(ctl, run, "release:done")
        self.assertEqual(released["state"], "IDLE")

    def test_correction_budget_requires_exact_one_increment_and_is_bounded(self):
        run, ctl = self.active_pair()
        run = mod.transition_run(run, ctl, expected_revision=1, transition_id="p2", next_phase="PR_OPEN", pr_number=77)
        ctl = mod.apply_transition_to_controller(ctl, run, "p2")
        run = mod.transition_run(run, ctl, expected_revision=2, transition_id="p3", next_phase="WAITING_CI")
        ctl = mod.apply_transition_to_controller(ctl, run, "p3")
        with self.assertRaisesRegex(ValueError, "increment exactly one"):
            mod.transition_run(run, ctl, expected_revision=3, transition_id="bad", next_phase="WAITING_CI", correction_count=2)
        run = mod.transition_run(run, ctl, expected_revision=3, transition_id="fix1", next_phase="WAITING_CI", correction_count=1)
        ctl = mod.apply_transition_to_controller(ctl, run, "fix1")
        run = mod.transition_run(run, ctl, expected_revision=4, transition_id="fix2", next_phase="WAITING_CI", correction_count=2)
        ctl = mod.apply_transition_to_controller(ctl, run, "fix2")
        with self.assertRaises(ValueError):
            mod.transition_run(run, ctl, expected_revision=5, transition_id="fix3", next_phase="WAITING_CI", correction_count=3)

    def test_stale_revision_and_stale_run_fail_closed(self):
        run, ctl = self.active_pair()
        with self.assertRaisesRegex(ValueError, "stale revision"):
            mod.transition_run(run, ctl, expected_revision=0, transition_id="stale", next_phase="PR_OPEN", pr_number=77)
        stale = copy.deepcopy(run)
        stale["run_id"] = str(uuid.UUID("123e4567-e89b-42d3-a456-426614174002"))
        with self.assertRaisesRegex(ValueError, "target/run mismatch|digest mismatch"):
            mod.transition_run(stale, ctl, expected_revision=1, transition_id="stale-run", next_phase="PR_OPEN", pr_number=77)

    def test_stopped_preserves_blocker_and_cannot_wake_resume(self):
        run, ctl = self.active_pair()
        stopped = mod.transition_run(
            run, ctl, expected_revision=1, transition_id="stop:1",
            next_phase="STOPPED", stop_reason="CI provider ambiguous", owner_gate="REAUTHORIZATION",
        )
        stopped_ctl = mod.apply_transition_to_controller(ctl, stopped, "stop:1")
        self.assertEqual(stopped_ctl["state"], "STOPPED")
        self.assertEqual(stopped["stop_reason"], "CI provider ambiguous")
        with self.assertRaisesRegex(ValueError, "ACTIVE controller|terminal"):
            mod.transition_run(stopped, stopped_ctl, expected_revision=2, transition_id="wake", next_phase="ACTIVE_SOURCE")

    def test_stopped_release_requires_explicit_abort_decision(self):
        run, ctl = self.active_pair()
        stopped = mod.transition_run(run, ctl, expected_revision=1, transition_id="stop", next_phase="STOPPED", stop_reason="scope drift")
        stopped_ctl = mod.apply_transition_to_controller(ctl, stopped, "stop")
        with self.assertRaisesRegex(ValueError, "explicit abort"):
            mod.release_aborted(stopped_ctl, stopped, "release", explicit_abort_authorized=False)
        released = mod.release_aborted(stopped_ctl, stopped, "release", explicit_abort_authorized=True)
        self.assertEqual(released["state"], "IDLE")

    def test_done_cannot_be_reused_as_authority(self):
        run, ctl = self.active_pair()
        run = mod.transition_run(run, ctl, expected_revision=1, transition_id="p2", next_phase="PR_OPEN", pr_number=77)
        ctl = mod.apply_transition_to_controller(ctl, run, "p2")
        run = mod.transition_run(run, ctl, expected_revision=2, transition_id="p3", next_phase="WAITING_CI")
        ctl = mod.apply_transition_to_controller(ctl, run, "p3")
        run = mod.transition_run(run, ctl, expected_revision=3, transition_id="p4", next_phase="READY")
        ctl = mod.apply_transition_to_controller(ctl, run, "p4")
        run = mod.transition_run(run, ctl, expected_revision=4, transition_id="p5", next_phase="DONE", completion=completion())
        ctl = mod.apply_transition_to_controller(ctl, run, "p5")
        with self.assertRaisesRegex(ValueError, "terminal"):
            mod.transition_run(run, ctl, expected_revision=5, transition_id="reuse", next_phase="ACTIVE_SOURCE")

    def test_lost_session_reconstruction_uses_github_state_only(self):
        run, ctl = self.active_pair()
        view1 = mod.reconstruct_normalized(run, ctl)
        view2 = mod.reconstruct_normalized(copy.deepcopy(run), copy.deepcopy(ctl))
        self.assertEqual(view1, view2)
        self.assertEqual(view1["phase"], "ACTIVE_SOURCE")

    def test_legacy_read_compatibility_reconciles_exact_duplicate_state(self):
        target = {"repository": REPO, "issue_number": 123, "scope_digest_sha256": SCOPE}
        controller = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID, "phase": "WAITING_CI",
                      "branch": "auto-full/123", "pr_number": 77, "correction_count": 1}
        activation = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID}
        status = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID, "phase": "WAITING_CI",
                  "pr_number": 77, "stop_reason": None, "owner_gate": None, "completion": None}
        view = mod.reconstruct_legacy(target=target, controller=controller, activation_receipt=activation, status_receipt=status)
        self.assertEqual(view["phase"], "WAITING_CI")
        self.assertEqual(view["pr_number"], 77)

    def test_legacy_collision_fails_closed(self):
        target = {"repository": REPO, "issue_number": 123, "scope_digest_sha256": SCOPE}
        controller = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID, "phase": "WAITING_CI",
                      "branch": "auto-full/123", "pr_number": 77, "correction_count": 1}
        activation = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID}
        status = {"repository": REPO, "issue_number": 123, "run_id": RUN_ID, "phase": "READY",
                  "pr_number": 77, "stop_reason": None, "owner_gate": "MERGE", "completion": None}
        with self.assertRaisesRegex(ValueError, "collision"):
            mod.reconstruct_legacy(target=target, controller=controller, activation_receipt=activation, status_receipt=status)

    def test_synthetic_reconstruction_cost_proves_fewer_objects_and_duplicates(self):
        legacy = mod.legacy_reconstruction_cost()
        normalized = mod.normalized_reconstruction_cost()
        self.assertLess(normalized.durable_objects, legacy.durable_objects)
        self.assertLess(normalized.duplicated_mutable_fields, legacy.duplicated_mutable_fields)
        self.assertEqual(normalized.durable_objects, 2)
        self.assertEqual(normalized.duplicated_mutable_fields, 0)

    def test_policy_preserves_authority_and_queue_boundaries(self):
        policy = json.loads((ROOT / "policy/auto-run-full-single-issue-state-v2.json").read_text())
        self.assertEqual(policy["status"], "SHARED_SOURCE_CONTRACT_NOT_ACTIVE_IN_CONSUMERS")
        self.assertFalse(policy["activation"]["consumer_auto_migration"])
        self.assertFalse(policy["activation"]["active_legacy_run_rewrite"])
        self.assertFalse(policy["authority"]["changes_merge_authority"])
        self.assertFalse(policy["authority"]["changes_live_authority"])
        self.assertFalse(policy["authority"]["creates_retry_rollback_cleanup_authority"])
        self.assertFalse(policy["queue_relationship"]["queue_v1_modified_by_this_contract"])
        self.assertFalse(policy["queue_relationship"]["queue_vnext_96_activated"])

    def test_receipts_and_controller_forbid_mutable_duplicate_control_state(self):
        policy = json.loads((ROOT / "policy/auto-run-full-single-issue-state-v2.json").read_text())
        self.assertFalse(policy["receipts"]["mutable_control_state_allowed"])
        self.assertFalse(policy["receipts"]["per_read_refresh_receipt_allowed"])
        self.assertFalse(policy["controller"]["copies_target_phase"])
        self.assertFalse(policy["controller"]["copies_branch_or_pr"])
        self.assertFalse(policy["controller"]["copies_ci_or_review"])

    def test_doc_has_ownership_compatibility_reconstruction_and_rollout_sections(self):
        doc = (ROOT / "docs/AUTO_RUN_FULL_SINGLE_ISSUE_STATE_V2.md").read_text()
        for marker in (
            "## 3. Canonical field ownership",
            "## 5. Minimal controller",
            "## 9. Legacy read compatibility",
            "## 10. Lost-session reconstruction",
            "## 11. WRITE_PREFLIGHT_COMPACT integration",
            "## 13. Rollout",
        ):
            self.assertIn(marker, doc)
        self.assertIn("Queue vNext `#96` remain inactive", doc)

if __name__ == "__main__":
    unittest.main(verbosity=2)
