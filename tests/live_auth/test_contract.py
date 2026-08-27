from __future__ import annotations

import importlib.util
import json
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "lint_live_auth.py"

spec = importlib.util.spec_from_file_location("lint_live_auth", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def valid_payload() -> dict:
    return {
        "schema": "rozkalns.live-auth.v1",
        "request_id": str(uuid.uuid4()),
        "queue_repository": "rozkalnsandris/ops-workflows",
        "queue_issue": 123,
        "source_repository": "rozkalnsandris/example",
        "source_sha": "0123456789abcdef0123456789abcdef01234567",
        "target_alias": "example-production",
        "operation_id": "example.application-deploy.v1",
        "expected_baseline": {"kind": "exact-sha", "value": "baseline-public-safe"},
        "mutation_budget": [{"category": "application-deploy", "max_operations": 1}],
        "rollback_policy": "NONE",
        "exclusions": ["database writes", "credential changes"],
        "dependencies": [],
    }


def body_for(payload: dict, *, suffix: str = "") -> str:
    encoded = json.dumps(payload, indent=2, sort_keys=False)
    return mod.START_MARKER + "\n```json\n" + encoded + "\n```\n" + mod.END_MARKER + suffix


class LiveAuthContractTests(unittest.TestCase):
    def test_valid_owner_envelope_passes(self):
        errors = mod.lint(
            "[LIVE-AUTH][PENDING] example-production",
            body_for(valid_payload()),
            actor_id=mod.OWNER_USER_ID,
            actor_type="User",
        )
        self.assertEqual(errors, [])

    def test_wrong_owner_or_bot_fails(self):
        body = body_for(valid_payload())
        self.assertIn("configured owner id", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body, actor_id=1, actor_type="User")[0])
        self.assertIn("author type must be User", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body,
            actor_id=mod.OWNER_USER_ID, actor_type="Bot")[0])

    def test_title_target_must_match_payload(self):
        self.assertEqual(
            mod.lint("[LIVE-AUTH][PENDING] other-target", body_for(valid_payload())),
            ["title target alias must equal payload target_alias"],
        )

    def test_duplicate_json_key_fails(self):
        raw = json.dumps(valid_payload())
        raw = raw[:-1] + ',"schema":"rozkalns.live-auth.v1"}'
        body = mod.START_MARKER + "\n```json\n" + raw + "\n```\n" + mod.END_MARKER
        self.assertIn("duplicate JSON key", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body)[0])

    def test_extra_field_fails(self):
        payload = valid_payload()
        payload["command"] = "bash -c anything"
        self.assertIn("keys mismatch", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_invalid_uuid_fails(self):
        payload = valid_payload()
        payload["request_id"] = "00000000-0000-0000-0000-000000000000"
        self.assertIn("UUIDv4", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_queue_repository_is_fixed(self):
        payload = valid_payload()
        payload["queue_repository"] = "other/repo"
        self.assertIn("queue_repository must be rozkalnsandris/ops-workflows", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_exact_lowercase_sha_required(self):
        payload = valid_payload()
        payload["source_sha"] = "A" * 40
        self.assertIn("source_sha format is invalid", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_duplicate_mutation_category_fails(self):
        payload = valid_payload()
        payload["mutation_budget"].append({"category": "application-deploy", "max_operations": 2})
        self.assertIn("duplicate mutation category", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_unsupported_rollback_fails(self):
        payload = valid_payload()
        payload["rollback_policy"] = "AUTO_MAGIC"
        self.assertIn("unsupported rollback_policy", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body_for(payload))[0])

    def test_exactly_one_authority_block_required(self):
        body = body_for(valid_payload())
        self.assertEqual(mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body + "\n" + body),
            ["exactly one LIVE-AUTH authority block is required"],
        )

    def test_body_size_ceiling(self):
        body = body_for(valid_payload(), suffix="\n" + ("x" * mod.MAX_BODY_BYTES))
        self.assertIn("issue body must contain", mod.lint(
            "[LIVE-AUTH][PENDING] example-production", body)[0])

    def test_machine_policy_is_fail_closed_and_read_only(self):
        policy = json.loads((ROOT / "policy" / "live-auth-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["canonical_repository"], mod.AUTHORIZATION_REPOSITORY)
        self.assertEqual(policy["canonical_repository_id"], mod.AUTHORIZATION_REPOSITORY_ID)
        self.assertEqual(policy["owner_user_id"], mod.OWNER_USER_ID)
        self.assertEqual(policy["authority"]["fixed_ttl_seconds"], mod.TTL_SECONDS)
        self.assertFalse(policy["authority"]["self_declared_actor_field_is_authority"])
        self.assertFalse(policy["executor_credential"]["authorization_surface_write_permission"])
        self.assertEqual(policy["executor_credential"]["authorization_surface_issues_permission"], "read")
        self.assertFalse(policy["binding"]["conditional_304_sufficient_for_authority_revalidation"])
        self.assertFalse(policy["receipts"]["authority"])
        self.assertFalse(policy["receipts"]["may_trigger_execution_or_retry"])

    def test_json_schema_matches_linter_field_set(self):
        schema = json.loads((ROOT / "policy" / "schemas" / "live-auth-v1.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(mod.PAYLOAD_FIELDS))
        self.assertEqual(set(schema["properties"]), set(mod.PAYLOAD_FIELDS))
        self.assertEqual(schema["properties"]["queue_repository"]["const"], mod.AUTHORIZATION_REPOSITORY)
        self.assertEqual(set(schema["properties"]["rollback_policy"]["enum"]), set(mod.ROLLBACK_POLICIES))

    def test_receipt_schema_cannot_be_authority(self):
        receipt = json.loads((ROOT / "policy" / "schemas" / "deploy-receipt-v1.schema.json").read_text())
        self.assertEqual(receipt["properties"]["schema"]["const"], "rozkalns.deploy-receipt.v1")
        policy = json.loads((ROOT / "policy" / "live-auth-v1.json").read_text())
        self.assertFalse(policy["receipts"]["authority"])
        self.assertFalse(policy["receipts"]["reporting_failure_replays_execution"])

    def test_issue_template_is_intentionally_non_passing_placeholder(self):
        template = (ROOT / ".github" / "ISSUE_TEMPLATE" / "live-auth.md").read_text()
        self.assertEqual(template.count(mod.START_MARKER), 1)
        self.assertEqual(template.count(mod.END_MARKER), 1)
        self.assertIn('title: "[LIVE-AUTH][PENDING] "', template)
        self.assertIn("REPLACE_WITH_CANONICAL_UUIDV4", template)

    def test_workflow_has_no_issue_write_permission(self):
        workflow = (ROOT / ".github" / "workflows" / "live-auth-contract.yml").read_text()
        self.assertIn("issues: read", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("write-all", workflow)
        self.assertIn("persist-credentials: false", workflow)

    def test_normative_doc_states_ready_is_not_authority(self):
        text = (ROOT / "docs" / "LIVE_AUTH_V1.md").read_text().lower()
        self.assertIn("eligibility only", text)
        self.assertIn("one live-auth issue per selected queue item", text)
        self.assertIn("read-only", text)
        self.assertIn("receipts are not authority", text)

    def test_shared_policy_keeps_ready_as_eligibility_only(self):
        policy = json.loads((ROOT / "policy" / "github-only-live-all-v1.json").read_text())
        self.assertFalse(policy["ready_rule"]["ready_is_execution_authorization"])
        deferred = policy["deferred_pull_authorization"]
        self.assertTrue(deferred["owner_decision_must_be_materialized_for_deferred_pull_executor"])
        self.assertFalse(deferred["github_only_may_create_live_auth"])
        self.assertFalse(deferred["bare_continuation_may_create_live_auth"])
        self.assertFalse(deferred["merge_may_create_live_auth"])
        self.assertFalse(deferred["executor_authorization_surface_write_allowed"])
        self.assertFalse(deferred["receipt_is_authority"])

    def test_shared_doc_distinguishes_direct_and_deferred_execution(self):
        text = (ROOT / "docs" / "GITHUB_ONLY_LIVE_ALL.md").read_text().lower()
        self.assertIn("ready is eligibility only", text)
        self.assertIn("direct same-session executor", text)
        self.assertIn("deferred rpi5 pull executor", text)
        self.assertIn("600-second ttl", text)
        self.assertIn("receipt is evidence only", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
