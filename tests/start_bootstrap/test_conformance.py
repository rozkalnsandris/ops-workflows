from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from start_bootstrap_model import (
    Candidate,
    WorkCycleContext,
    decide_work_cycle,
    github_only_active_for_command,
    render_compact_terminal_response,
    route_final_state,
    select_canonical_lane,
    validate_ready_dependency_graph,
)

EXCLUDED = ("automation-fixture", "do-not-merge", "superseded", "parked-historical")
POLICY = json.loads((ROOT / "policy" / "agent-work-cycle-v1.json").read_text(encoding="utf-8"))


class StartBootstrapConformance(unittest.TestCase):
    def test_plain_start_does_not_activate_github_only(self):
        self.assertFalse(github_only_active_for_command("START dashboard_RPi5"))

    def test_explicit_start_activates_github_only(self):
        self.assertTrue(github_only_active_for_command("START dashboard_RPi5 GITHUB-ONLY"))

    def test_human_alias_start_activates_github_only(self):
        self.assertTrue(github_only_active_for_command("START dashboard_RPi5 git hub only"))

    def test_direct_commands_activate_github_only(self):
        self.assertTrue(github_only_active_for_command("GITHUB-ONLY"))
        self.assertTrue(github_only_active_for_command("git hub only"))

    def test_plain_start_preserves_already_active_mode(self):
        self.assertTrue(
            github_only_active_for_command("START dashboard_RPi5", already_active=True)
        )

    def test_unrelated_github_only_text_does_not_activate(self):
        self.assertFalse(
            github_only_active_for_command("START dashboard_RPi5 please use GITHUB-ONLY")
        )

    def test_no_issue_but_focused_pr_continues(self):
        selected, state = select_canonical_lane([
            Candidate("active_focused_pr_blocking_current_phase", "pr:42")
        ], excluded_labels=EXCLUDED)
        self.assertEqual(("pr:42", "SELECTED"), (selected, state))

    def test_handoff_beats_focused_pr(self):
        selected, _ = select_canonical_lane([
            Candidate("active_focused_pr_blocking_current_phase", "pr:42"),
            Candidate("explicit_current_handoff", "handoff:1"),
        ], excluded_labels=EXCLUDED)
        self.assertEqual("handoff:1", selected)

    def test_no_canonical_evidence_is_idle(self):
        self.assertEqual((None, "IDLE"), select_canonical_lane([], excluded_labels=EXCLUDED))

    def test_equally_authoritative_lanes_fail_closed(self):
        selected, state = select_canonical_lane([
            Candidate("active_issue_declared_as_current", "issue:10", phase_priority=1),
            Candidate("active_issue_declared_as_current", "issue:11", phase_priority=1),
        ], excluded_labels=EXCLUDED)
        self.assertIsNone(selected)
        self.assertEqual("AMBIGUOUS_CANONICAL_LANE", state)

    def test_explicit_priority_breaks_tie(self):
        selected, state = select_canonical_lane([
            Candidate("active_issue_declared_as_current", "issue:10", phase_priority=2),
            Candidate("active_issue_declared_as_current", "issue:11", phase_priority=1),
        ], excluded_labels=EXCLUDED)
        self.assertEqual(("issue:11", "SELECTED"), (selected, state))

    def test_api_order_does_not_change_lane(self):
        base = [
            Candidate("active_focused_pr_blocking_current_phase", "pr:7", phase_priority=2),
            Candidate("active_focused_pr_blocking_current_phase", "pr:8", phase_priority=1),
            Candidate("active_issue_declared_as_current", "issue:9", phase_priority=0),
        ]
        observed = set()
        for seed in range(100):
            values = list(base)
            random.Random(seed).shuffle(values)
            observed.add(select_canonical_lane(values, excluded_labels=EXCLUDED))
        self.assertEqual({("pr:8", "SELECTED")}, observed)

    def test_do_not_merge_fixture_is_excluded(self):
        selected, state = select_canonical_lane([
            Candidate("active_focused_pr_blocking_current_phase", "pr:3", labels=("do-not-merge",)),
        ], excluded_labels=EXCLUDED)
        self.assertEqual((None, "IDLE"), (selected, state))

    def test_final_state_router(self):
        self.assertEqual("READY_FOR_MERGE", route_final_state(merge_ready=True))
        self.assertEqual("PARKED", route_final_state(deferred_ready=True))
        self.assertEqual("STOP_ERROR", route_final_state(source_error=True))
        self.assertEqual("NEW_SCOPE_OR_RISK", route_final_state(new_scope_or_risk=True))
        self.assertEqual("AMBIGUOUS_CANONICAL_LANE", route_final_state(ambiguous_lane=True))
        self.assertEqual("IDLE", route_final_state(canonical_work_exists=False))

    def test_ready_dependency_cycle_fails_before_mutation(self):
        valid, reason = validate_ready_dependency_graph([
            {"issue": 1, "state": "READY", "target": "a", "dependencies": [2]},
            {"issue": 2, "state": "READY", "target": "b", "dependencies": [1]},
        ])
        self.assertEqual((False, "DEPENDENCY_CYCLE"), (valid, reason))

    def test_unordered_same_target_fails_before_mutation(self):
        valid, reason = validate_ready_dependency_graph([
            {"issue": 1, "state": "READY", "target": "prod", "dependencies": []},
            {"issue": 2, "state": "READY", "target": "prod", "dependencies": []},
        ])
        self.assertEqual((False, "UNORDERED_SAME_TARGET"), (valid, reason))

    def test_ordered_same_target_is_valid(self):
        valid, reason = validate_ready_dependency_graph([
            {"issue": 1, "state": "READY", "target": "prod", "dependencies": []},
            {"issue": 2, "state": "READY", "target": "prod", "dependencies": [1]},
        ])
        self.assertEqual((True, "OK"), (valid, reason))

    # FAST-LANE v2.3 B / issue #121 scenarios

    def test_start_source_issue_auto_continues_safe_work(self):
        decision = decide_work_cycle(
            WorkCycleContext(safe_same_scope_work_remaining=True),
            repo="ops-workflows",
        )
        self.assertEqual("CONTINUE_SAFE_WORK", decision.disposition)
        self.assertFalse(decision.terminal)
        self.assertFalse(decision.action_required)
        self.assertIsNone(decision.final_command)

    def test_pending_ci_waits_only_when_no_safe_advance_exists(self):
        decision = decide_work_cycle(
            WorkCycleContext(waiting_external=True),
            repo="ops-workflows",
        )
        self.assertEqual("WAIT_EXTERNAL", decision.disposition)
        self.assertTrue(decision.terminal)
        self.assertFalse(decision.action_required)
        self.assertEqual("SYNC ops-workflows", decision.final_command)

    def test_explicit_merge_gate_stops_with_exact_owner_command(self):
        command = "MERGE ops-workflows #125 HEAD=abc METHOD=SQUASH NO-LIVE"
        decision = decide_work_cycle(
            WorkCycleContext(merge_ready=True),
            repo="ops-workflows",
            merge_command=command,
        )
        self.assertEqual("OWNER_GATE_MERGE", decision.disposition)
        self.assertTrue(decision.terminal)
        self.assertTrue(decision.action_required)
        self.assertEqual(command, decision.final_command)

    def test_repo_local_full_merge_authority_does_not_add_generic_gate(self):
        decision = decide_work_cycle(
            WorkCycleContext(merge_ready=True, full_merge_authority=True),
            repo="example",
        )
        self.assertEqual("CONTINUE_SAFE_WORK", decision.disposition)
        self.assertFalse(decision.terminal)
        self.assertFalse(decision.action_required)

    def test_live_requirement_stops_before_live_mutation(self):
        command = "AUTHORIZE example LIVE TARGET=prod SHA=abc"
        decision = decide_work_cycle(
            WorkCycleContext(live_gate_required=True),
            repo="example",
            live_command=command,
        )
        self.assertEqual("OWNER_GATE_LIVE", decision.disposition)
        self.assertTrue(decision.terminal)
        self.assertTrue(decision.action_required)
        self.assertEqual(command, decision.final_command)

    def test_sync_refreshes_selected_lane_without_repo_wide_inventory(self):
        self.assertTrue(POLICY["execution"]["sync_refreshes_selected_lane_only"])
        self.assertFalse(POLICY["retrieval"]["repo_wide_audit_by_default"])

    def test_turpini_preserves_scope_and_never_creates_authority(self):
        self.assertTrue(POLICY["execution"]["continue_preserves_exact_scope"])
        self.assertTrue(POLICY["next_command_contract"]["never_implies_merge_or_live_authority"])
        self.assertFalse(POLICY["owner_gates"]["automatic_retry_rollback_cleanup"])

    def test_compact_terminal_response_has_one_final_actionable_command(self):
        decision = decide_work_cycle(
            WorkCycleContext(waiting_external=True),
            repo="ops-workflows",
        )
        rendered = render_compact_terminal_response(
            decision,
            evidence=("exact head unchanged", "CI pending"),
            done=("source work complete",),
            blocker="waiting for CI",
        )
        self.assertTrue(rendered.startswith("STATE: WAIT_EXTERNAL"))
        self.assertEqual(1, rendered.count("SYNC ops-workflows"))
        self.assertEqual("SYNC ops-workflows", rendered.splitlines()[-1])
        self.assertNotIn("ACTION REQUIRED", rendered)

    def test_action_required_only_appears_for_real_owner_gate(self):
        wait = decide_work_cycle(
            WorkCycleContext(waiting_external=True),
            repo="ops-workflows",
        )
        merge = decide_work_cycle(
            WorkCycleContext(merge_ready=True),
            repo="ops-workflows",
            merge_command="MERGE ops-workflows #1 HEAD=abc METHOD=SQUASH NO-LIVE",
        )
        self.assertNotIn("ACTION REQUIRED", render_compact_terminal_response(wait))
        self.assertIn("ACTION REQUIRED", render_compact_terminal_response(merge))

    def test_audit_handoff_remains_explicit_deep_mode(self):
        self.assertTrue(POLICY["execution"]["audit_handoff_is_explicit_deep_mode"])
        self.assertFalse(POLICY["retrieval"]["repo_wide_audit_by_default"])

    def test_safe_work_wins_over_external_wait_until_safe_advance_is_exhausted(self):
        decision = decide_work_cycle(
            WorkCycleContext(
                safe_same_scope_work_remaining=True,
                waiting_external=True,
            ),
            repo="ops-workflows",
        )
        self.assertEqual("CONTINUE_SAFE_WORK", decision.disposition)
        self.assertFalse(decision.terminal)

    def test_done_uses_start_as_single_next_command(self):
        decision = decide_work_cycle(WorkCycleContext(done=True), repo="ops-workflows")
        rendered = render_compact_terminal_response(decision, done=("current outcome complete",))
        self.assertEqual("START ops-workflows", rendered.splitlines()[-1])
        self.assertNotIn("ACTION REQUIRED", rendered)

    def test_evidence_is_bounded_to_four_decisive_facts(self):
        decision = decide_work_cycle(WorkCycleContext(done=True), repo="ops-workflows")
        with self.assertRaises(ValueError):
            render_compact_terminal_response(
                decision,
                evidence=("1", "2", "3", "4", "5"),
            )


if __name__ == "__main__":
    unittest.main()
