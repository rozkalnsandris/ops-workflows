from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/validate_auto_run_full_queue_guards.py"
SPEC = importlib.util.spec_from_file_location("queue_guards", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

GuardError = MODULE.GuardError


class QueueGuardsTests(unittest.TestCase):
    sha = "a" * 40
    repository = "rozkalnsandris/example-consumer"

    def source_canary(self, proven: bool = False) -> dict:
        if not proven:
            return {
                "status": "NOT_PROVEN",
                "queue_id": None,
                "controller_issue_number": None,
                "ordered_issue_numbers": [],
                "activation_main_sha": None,
                "final_main_sha": None,
                "authorization_receipt_sha256": None,
                "completion_receipt_sha256": None,
            }
        return {
            "status": "QUEUE_SOURCE_COMPLETE",
            "queue_id": "queue-canary-2026-09",
            "controller_issue_number": 321,
            "ordered_issue_numbers": [123],
            "activation_main_sha": "b" * 40,
            "final_main_sha": "c" * 40,
            "authorization_receipt_sha256": "d" * 64,
            "completion_receipt_sha256": "e" * 64,
        }

    def manifest(
        self,
        phase: str = "SOURCE_ONLY_CANARY",
        live_mode: str = "DISABLED",
        source_proven: bool | None = None,
    ) -> dict:
        if source_proven is None:
            source_proven = phase in {"LIVE_CANARY_READY", "MIGRATED"}
        return {
            "schema": "rozkalns.auto-run-full-queue-adoption.v1",
            "repository": self.repository,
            "shared_contract_sha": self.sha,
            "adoption_phase": phase,
            "queue": {
                "command_active": True,
                "maximum_items": 10,
                "maximum_active_items": 1,
                "batch_source_authority": True,
                "batch_merge_authority": True,
                "live_authority": False,
            },
            "source_canary": self.source_canary(source_proven),
            "final_live": {
                "mode": live_mode,
                "double_execution_paths_allowed": False,
                "deferred_rpi5_requires_live_auth_v1": True,
            },
            "boundaries": {
                "ops_workflows_executes_production": False,
                "ops_workflows_stores_production_credentials": False,
                "consumer_owns_rollout_adapter": True,
                "repository_local_stricter_rules_win": True,
            },
        }

    def caller_root(self, manifest: dict, pin: str | None = None) -> tempfile.TemporaryDirectory:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / ".github/workflows").mkdir(parents=True)
        (root / ".github/auto-run-full-queue-adoption-v1.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        ref = pin if pin is not None else manifest["shared_contract_sha"]
        (root / ".github/workflows/queue-guard.yml").write_text(
            "name: queue guard\n"
            "on: [pull_request]\n"
            "jobs:\n"
            "  guard:\n"
            "    uses: rozkalnsandris/ops-workflows/.github/workflows/"
            f"auto-run-full-queue-adoption-guard.yml@{ref}\n"
            "    with:\n"
            f"      canonical_policy_sha: {manifest['shared_contract_sha']}\n",
            encoding="utf-8",
        )
        return temp

    def validate_manifest(self, manifest: dict, pin: str | None = None) -> None:
        temp = self.caller_root(manifest, pin)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        MODULE.validate_adoption(
            canonical_root=ROOT,
            manifest_path=root / ".github/auto-run-full-queue-adoption-v1.json",
            expected_repository=self.repository,
            expected_sha=self.sha,
            caller_root=root,
        )

    def test_shared_composition_passes(self) -> None:
        checks = MODULE.validate_composition(ROOT)
        self.assertGreaterEqual(checks, 50)

    def test_source_only_canary_manifest_passes_without_proof(self) -> None:
        self.validate_manifest(self.manifest())

    def test_source_only_canary_may_record_completed_proof_while_live_disabled(self) -> None:
        self.validate_manifest(self.manifest(source_proven=True))

    def test_live_canary_simple_live_manifest_passes_with_source_proof(self) -> None:
        self.validate_manifest(
            self.manifest("LIVE_CANARY_READY", "SIMPLE_LIVE_OWNER_DRIVEN")
        )

    def test_live_canary_auto_live_manifest_passes_with_source_proof(self) -> None:
        self.validate_manifest(
            self.manifest("LIVE_CANARY_READY", "AUTO_LIVE_V1_STATIC")
        )

    def test_live_canary_without_source_proof_is_rejected(self) -> None:
        manifest = self.manifest(
            "LIVE_CANARY_READY",
            "SIMPLE_LIVE_OWNER_DRIVEN",
            source_proven=False,
        )
        with self.assertRaisesRegex(
            GuardError, "requires QUEUE_SOURCE_COMPLETE source-canary evidence"
        ):
            self.validate_manifest(manifest)

    def test_migrated_without_source_proof_is_rejected(self) -> None:
        manifest = self.manifest("MIGRATED", "DISABLED", source_proven=False)
        with self.assertRaisesRegex(
            GuardError, "MIGRATED requires QUEUE_SOURCE_COMPLETE"
        ):
            self.validate_manifest(manifest)

    def test_completed_source_canary_requires_unique_ordered_issues(self) -> None:
        manifest = self.manifest(
            "LIVE_CANARY_READY", "SIMPLE_LIVE_OWNER_DRIVEN"
        )
        manifest["source_canary"]["ordered_issue_numbers"] = [123, 123]
        with self.assertRaisesRegex(GuardError, "must be unique"):
            self.validate_manifest(manifest)

    def test_completed_source_canary_requires_receipt_hashes(self) -> None:
        manifest = self.manifest(
            "LIVE_CANARY_READY", "SIMPLE_LIVE_OWNER_DRIVEN"
        )
        manifest["source_canary"]["completion_receipt_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(GuardError, "exact lowercase SHA-256"):
            self.validate_manifest(manifest)

    def test_not_proven_source_canary_cannot_smuggle_evidence(self) -> None:
        manifest = self.manifest()
        manifest["source_canary"]["queue_id"] = "phantom-queue"
        with self.assertRaisesRegex(GuardError, "queue_id must be null"):
            self.validate_manifest(manifest)

    def test_source_only_canary_cannot_enable_live(self) -> None:
        manifest = self.manifest("SOURCE_ONLY_CANARY", "SIMPLE_LIVE_OWNER_DRIVEN")
        with self.assertRaisesRegex(GuardError, "SOURCE_ONLY_CANARY"):
            self.validate_manifest(manifest)

    def test_live_canary_requires_final_live_mode(self) -> None:
        manifest = self.manifest("LIVE_CANARY_READY", "DISABLED")
        with self.assertRaisesRegex(GuardError, "requires one explicit final LIVE mode"):
            self.validate_manifest(manifest)

    def test_queue_never_gets_live_authority(self) -> None:
        manifest = self.manifest()
        manifest["queue"]["live_authority"] = True
        with self.assertRaisesRegex(GuardError, "never grant LIVE authority"):
            self.validate_manifest(manifest)

    def test_one_active_item_is_enforced(self) -> None:
        manifest = self.manifest()
        manifest["queue"]["maximum_active_items"] = 2
        with self.assertRaisesRegex(GuardError, "maximum_active_items"):
            self.validate_manifest(manifest)

    def test_double_final_live_paths_are_forbidden(self) -> None:
        manifest = self.manifest("LIVE_CANARY_READY", "SIMPLE_LIVE_OWNER_DRIVEN")
        manifest["final_live"]["double_execution_paths_allowed"] = True
        with self.assertRaisesRegex(GuardError, "double final-LIVE"):
            self.validate_manifest(manifest)

    def test_deferred_rpi5_live_auth_is_preserved(self) -> None:
        manifest = self.manifest("LIVE_CANARY_READY", "SIMPLE_LIVE_OWNER_DRIVEN")
        manifest["final_live"]["deferred_rpi5_requires_live_auth_v1"] = False
        with self.assertRaisesRegex(GuardError, "RPi5 LIVE-AUTH"):
            self.validate_manifest(manifest)

    def test_repository_identity_must_match(self) -> None:
        manifest = self.manifest()
        manifest["repository"] = "rozkalnsandris/other"
        temp = self.caller_root(manifest)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        with self.assertRaisesRegex(GuardError, "does not match caller repository"):
            MODULE.validate_adoption(
                canonical_root=ROOT,
                manifest_path=root / ".github/auto-run-full-queue-adoption-v1.json",
                expected_repository=self.repository,
                expected_sha=self.sha,
                caller_root=root,
            )

    def test_mutable_reusable_guard_pin_is_rejected(self) -> None:
        manifest = self.manifest()
        with self.assertRaisesRegex(GuardError, "mutable/non-SHA"):
            self.validate_manifest(manifest, pin="main")

    def test_reusable_guard_pin_must_match_manifest_sha(self) -> None:
        manifest = self.manifest()
        with self.assertRaisesRegex(GuardError, "does not match manifest"):
            self.validate_manifest(manifest, pin="b" * 40)

    def test_every_reusable_guard_pin_must_match_manifest_sha(self) -> None:
        manifest = self.manifest()
        temp = self.caller_root(manifest)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / ".github/workflows/queue-guard-second.yml").write_text(
            "name: second queue guard\n"
            "on: [pull_request]\n"
            "jobs:\n"
            "  guard:\n"
            "    uses: rozkalnsandris/ops-workflows/.github/workflows/"
            f"auto-run-full-queue-adoption-guard.yml@{'b' * 40}\n"
            "    with:\n"
            f"      canonical_policy_sha: {manifest['shared_contract_sha']}\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(GuardError, "does not match manifest"):
            MODULE.validate_adoption(
                canonical_root=ROOT,
                manifest_path=root / ".github/auto-run-full-queue-adoption-v1.json",
                expected_repository=self.repository,
                expected_sha=self.sha,
                caller_root=root,
            )

    def test_unknown_manifest_field_is_rejected(self) -> None:
        manifest = self.manifest()
        manifest["extra"] = True
        with self.assertRaisesRegex(GuardError, "unknown fields"):
            self.validate_manifest(manifest)

    def test_composition_rejects_event_payload_authority_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / "policy", root / "policy")
            path = root / "policy/auto-run-full-queue-resume-v1.json"
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["canonical_state"]["event_payload_is_authority"] = True
            path.write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaisesRegex(GuardError, "event payload became authority"):
                MODULE.validate_composition(root)

    def test_composition_rejects_simple_live_queue_authority_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / "policy", root / "policy")
            path = root / "policy/simple-live-v1.json"
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["activation"]["queue_authorizes_live"] = True
            path.write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaisesRegex(GuardError, "A5 queue gained LIVE authority"):
                MODULE.validate_composition(root)

    def test_composition_rejects_auto_live_merge_authority_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / "policy", root / "policy")
            path = root / "policy/auto-live-v1.json"
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["merge"]["authorizes_live_mutation"] = True
            path.write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaisesRegex(GuardError, "Auto-Live merge gained LIVE authority"):
                MODULE.validate_composition(root)

    def test_composition_rejects_phase_advance_without_evidence_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / "policy", root / "policy")
            path = root / "policy/auto-run-full-queue-guards-v1.json"
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["consumer_adoption"][
                "live_canary_requires_queue_source_complete_evidence"
            ] = False
            path.write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaisesRegex(
                GuardError, "consumer adoption invariant drifted"
            ):
                MODULE.validate_composition(root)


if __name__ == "__main__":
    unittest.main()
