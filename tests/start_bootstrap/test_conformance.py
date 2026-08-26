from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from start_bootstrap_model import (
    Candidate,
    github_only_active_for_command,
    route_final_state,
    select_canonical_lane,
    validate_ready_dependency_graph,
)

EXCLUDED = ("automation-fixture", "do-not-merge", "superseded", "parked-historical")


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


if __name__ == "__main__":
    unittest.main()
