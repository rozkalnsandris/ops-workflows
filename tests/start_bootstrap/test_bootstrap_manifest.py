from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from agent_bootstrap_manifest import (
    ManifestValidationError,
    load_manifest,
    resolve_bootstrap,
    validate_manifest,
)

MANIFEST_PATH = ROOT / ".github" / "agent-bootstrap.json"
POLICY_PATH = ROOT / "policy" / "agent-bootstrap-v1.json"
SCHEMA_PATH = ROOT / "policy" / "schemas" / "agent-bootstrap-v1.schema.json"
WORK_CYCLE_DOC = ROOT / "docs" / "AGENT_WORK_CYCLE_V1.md"
API_DOC = ROOT / "docs" / "GITHUB_API_ACCESS_V1.md"
BOOTSTRAP_DOC = ROOT / "docs" / "BOOTSTRAP_MANIFEST_V1.md"
AGENTS_PATH = ROOT / "AGENTS.md"


class BootstrapManifestV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_canonical_manifest_validates_and_routes(self):
        loaded = load_manifest(MANIFEST_PATH, repo_root=ROOT)
        self.assertEqual("rozkalnsandris/ops-workflows", loaded["repository"])
        resolution = resolve_bootstrap(ROOT)
        self.assertEqual("MANIFEST_ROUTED", resolution.status)
        self.assertEqual("AGENTS.md", resolution.rules_path)

    def test_policy_identity_and_authority_boundary(self):
        self.assertEqual("rozkalns.agent-bootstrap-policy.v1", self.policy["schema"])
        self.assertTrue(self.policy["routing_only"])
        self.assertEqual("GITHUB", self.policy["canonical_mutable_state_source"])
        authority = self.policy["authority"]
        for key, value in authority.items():
            self.assertFalse(value, key)

    def test_schema_is_closed_and_narrow(self):
        self.assertFalse(self.schema["additionalProperties"])
        required = set(self.schema["required"])
        self.assertEqual(
            {
                "schema",
                "repository",
                "shared_policy",
                "rules",
                "continuation",
                "automation",
                "deployment_profile",
            },
            required,
        )
        for section in ("shared_policy", "rules", "automation"):
            self.assertFalse(
                self.schema["properties"][section]["additionalProperties"],
                section,
            )

    def test_unknown_or_mutable_top_level_field_is_rejected(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["current_main_sha"] = "a" * 40
        with self.assertRaises(ManifestValidationError):
            validate_manifest(candidate, repo_root=ROOT)

    def test_nested_authority_or_secret_like_field_is_rejected(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["automation"]["token"] = "not-a-real-token"
        with self.assertRaises(ManifestValidationError):
            validate_manifest(candidate, repo_root=ROOT)

    def test_mutable_truth_is_not_present_in_canonical_manifest(self):
        serialized = json.dumps(self.manifest, sort_keys=True).casefold()
        for key in self.policy["forbidden_mutable_truth"]:
            self.assertNotIn(f'"{key.casefold()}"', serialized)

    def test_missing_manifest_preserves_legacy_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
            resolution = resolve_bootstrap(root)
            self.assertEqual("LEGACY_FALLBACK", resolution.status)
            self.assertEqual("AGENTS.md", resolution.rules_path)

    def test_invalid_manifest_falls_back_when_local_rules_are_unambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github").mkdir()
            (root / ".github" / "agent-bootstrap.json").write_text(
                '{"schema":"broken"}',
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
            resolution = resolve_bootstrap(root)
            self.assertEqual("MANIFEST_INVALID_FALLBACK", resolution.status)
            self.assertEqual("AGENTS.md", resolution.rules_path)

    def test_invalid_manifest_without_local_rules_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github").mkdir()
            (root / ".github" / "agent-bootstrap.json").write_text(
                '{"schema":"broken"}',
                encoding="utf-8",
            )
            resolution = resolve_bootstrap(root)
            self.assertEqual("STOP_AMBIGUOUS", resolution.status)
            self.assertIsNone(resolution.rules_path)

    def test_missing_referenced_shared_surface_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github").mkdir()
            (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
            (root / ".github" / "agent-bootstrap.json").write_text(
                json.dumps(self.manifest),
                encoding="utf-8",
            )
            resolution = resolve_bootstrap(root)
            self.assertEqual("MANIFEST_INVALID_FALLBACK", resolution.status)
            self.assertIn("referenced canonical surface missing", resolution.reason or "")

    def test_bootstrap_payload_is_materially_smaller_than_rules_document(self):
        manifest_bytes = len(MANIFEST_PATH.read_bytes())
        agents_bytes = len(AGENTS_PATH.read_bytes())
        self.assertLess(manifest_bytes * 4, agents_bytes)

    def test_human_contracts_reference_bootstrap_manifest(self):
        bootstrap_doc = BOOTSTRAP_DOC.read_text(encoding="utf-8")
        work_cycle = WORK_CYCLE_DOC.read_text(encoding="utf-8")
        api_doc = API_DOC.read_text(encoding="utf-8")
        self.assertIn("BOOTSTRAP_MANIFEST_V1", bootstrap_doc)
        self.assertIn("docs/BOOTSTRAP_MANIFEST_V1.md", work_cycle)
        self.assertIn("docs/BOOTSTRAP_MANIFEST_V1.md", api_doc)
        self.assertIn("routing", work_cycle.casefold())
        self.assertIn("BOOTSTRAP_MINIMAL", api_doc)

    def test_queue_and_deploy_profiles_are_descriptive_only(self):
        automation = self.manifest["automation"]
        self.assertEqual("inactive", automation["queue_mode"])
        self.assertEqual("source-only", self.manifest["deployment_profile"])
        self.assertTrue(automation["fast_lane"])
        self.assertTrue(automation["auto_run_full"])


if __name__ == "__main__":
    unittest.main()
