from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class QueueNormalizationGateTests(unittest.TestCase):
    def test_live_auth_machine_policy_blocks_ambiguous_queue_mapping(self):
        policy = json.loads((ROOT / "policy" / "live-auth-v1.json").read_text(encoding="utf-8"))
        binding = policy["binding"]
        self.assertTrue(binding["normalized_queue_contract_required_before_deferred_execution"])
        self.assertEqual(binding["normalized_queue_contract_owner"], "RPi5_main_P4_STATIC_OPERATION_ADAPTER")
        self.assertEqual(
            binding["missing_or_ambiguous_queue_normalization"],
            "NOT_EXECUTABLE_VIA_DEFERRED_PULL",
        )

    def test_shared_policy_leaves_unmappable_ready_item_ready_not_selected(self):
        policy = json.loads(
            (ROOT / "policy" / "github-only-live-all-v1.json").read_text(encoding="utf-8")
        )
        deferred = policy["deferred_pull_authorization"]
        self.assertTrue(deferred["normalized_queue_contract_required"])
        self.assertEqual(
            deferred["missing_or_ambiguous_queue_normalization"],
            "LEAVE_READY_NOT_SELECTED",
        )
        doc = (ROOT / "docs" / "GITHUB_ONLY_LIVE_ALL.md").read_text(encoding="utf-8").lower()
        self.assertIn("queue-normalization/operation adapter", doc)
        self.assertIn("leave it ready/not-selected", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
