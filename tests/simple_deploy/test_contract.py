from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_simple_deploy import ValidationError, validate_manifest, validate_root

ROOT = Path(__file__).resolve().parents[2]


def valid_manifest() -> dict:
    return {
        "schema": "rozkalns.simple-deploy.consumer.v1",
        "repository": "rozkalnsandris/example-service",
        "image": "ghcr.io/rozkalnsandris/example-service",
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile",
            "architecture": "linux/arm64",
        },
        "target": {
            "alias": "example-service-rpi5",
            "runtime_class": "rpi5-compose",
        },
        "compose": {
            "project": "example-service",
            "file": "deploy/docker-compose.production.yml",
            "service": "web",
        },
        "health": {
            "liveness_path": "/health",
            "readiness": {"state": "required", "path": "/ready"},
        },
        "persistence": {"volumes": ["example_data"]},
        "registry": {"pull_profile": "public-anonymous-pull"},
        "forbidden_operations": [
            "database-schema-data-mutation",
            "destructive-recovery",
            "secrets-credentials-permissions",
            "cloudflare-dns-network",
            "private-provider-activation",
            "unrelated-host-control",
        ],
    }


class SimpleDeployContractTests(unittest.TestCase):
    def test_repository_contract_passes(self) -> None:
        validate_root(ROOT)

    def test_valid_consumer_manifest_is_caller_bound(self) -> None:
        result = validate_manifest(valid_manifest(), "rozkalnsandris/example-service")
        self.assertEqual(result["image"], "ghcr.io/rozkalnsandris/example-service")
        self.assertEqual(result["target_alias"], "example-service-rpi5")
        self.assertRegex(result["manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_unknown_command_field_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["command"] = "docker compose up"
        with self.assertRaisesRegex(ValidationError, "forbidden/unknown"):
            validate_manifest(manifest)

    def test_unknown_secret_field_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["registry"]["token"] = "secret"
        with self.assertRaisesRegex(ValidationError, "forbidden/unknown"):
            validate_manifest(manifest)

    def test_arbitrary_path_traversal_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["build"]["context"] = "../outside"
        with self.assertRaisesRegex(ValidationError, "dot traversal"):
            validate_manifest(manifest)

    def test_image_must_match_caller_repository(self) -> None:
        manifest = valid_manifest()
        manifest["image"] = "ghcr.io/rozkalnsandris/other-service"
        with self.assertRaisesRegex(ValidationError, "caller-bound GHCR identity"):
            validate_manifest(manifest)

    def test_repository_must_match_caller(self) -> None:
        with self.assertRaisesRegex(ValidationError, "caller repository"):
            validate_manifest(valid_manifest(), "rozkalnsandris/other-service")

    def test_architecture_is_arm64_only_in_v1(self) -> None:
        manifest = valid_manifest()
        manifest["build"]["architecture"] = "linux/amd64"
        with self.assertRaisesRegex(ValidationError, "linux/arm64"):
            validate_manifest(manifest)

    def test_readiness_not_applicable_is_explicit(self) -> None:
        manifest = valid_manifest()
        manifest["health"]["readiness"] = {"state": "not-applicable"}
        result = validate_manifest(manifest)
        self.assertEqual(result["readiness_state"], "not-applicable")
        self.assertEqual(result["readiness_path"], "")

    def test_readiness_not_applicable_rejects_fake_path(self) -> None:
        manifest = valid_manifest()
        manifest["health"]["readiness"] = {"state": "not-applicable", "path": "/ready"}
        with self.assertRaisesRegex(ValidationError, "forbidden/unknown"):
            validate_manifest(manifest)

    def test_persistence_identity_is_explicit_even_when_empty(self) -> None:
        manifest = valid_manifest()
        manifest["persistence"] = {"volumes": []}
        result = validate_manifest(manifest)
        self.assertEqual(result["persistence_json"], "[]")

    def test_missing_sensitive_exclusion_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["forbidden_operations"].remove("database-schema-data-mutation")
        with self.assertRaisesRegex(ValidationError, "complete fixed v1"):
            validate_manifest(manifest)

    def test_duplicate_persistence_volume_fails_closed(self) -> None:
        manifest = valid_manifest()
        manifest["persistence"]["volumes"] = ["example_data", "example_data"]
        with self.assertRaisesRegex(ValidationError, "duplicates"):
            validate_manifest(manifest)

    def test_manifest_digest_is_order_independent(self) -> None:
        first = validate_manifest(valid_manifest())["manifest_sha256"]
        reordered = json.loads(json.dumps(valid_manifest(), sort_keys=True))
        second = validate_manifest(reordered)["manifest_sha256"]
        self.assertEqual(first, second)

    def test_github_output_is_public_safe_single_line(self) -> None:
        manifest = valid_manifest()
        manifest["target"]["alias"] = "bad\noutput"
        with self.assertRaises(ValidationError):
            validate_manifest(manifest)

    def test_policy_forbids_runtime_credentials_and_sensitive_mutation(self) -> None:
        policy = json.loads((ROOT / "policy" / "simple-deploy-v1.json").read_text(encoding="utf-8"))
        self.assertFalse(policy["registry"]["workflow_accepts_runtime_registry_credentials"])
        self.assertFalse(policy["boundaries"]["ops_workflows_executes_rpi5_mutation"])
        self.assertFalse(policy["boundaries"]["ordinary_deploy_includes_database_or_data_mutation"])
        self.assertFalse(policy["boundaries"]["ordinary_deploy_includes_network_or_cloudflare_mutation"])
        self.assertTrue(policy["compatibility"]["simple_live_remains_for_sensitive_or_exceptional_operations"])
        self.assertTrue(policy["compatibility"]["queue_vnext_blocked_until_fleet_stable"])


if __name__ == "__main__":
    unittest.main()
