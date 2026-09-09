from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_auto_run_full_queue_authorization.py"

spec = importlib.util.spec_from_file_location("queue_auth", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def digest_for(number: int, title: str = "Issue", body: str = "Do the bounded thing") -> str:
    return mod.canonical_scope_digest("rozkalnsandris/example", number, title, body)


def valid_payload() -> dict:
    return {
        "schema": mod.SCHEMA,
        "queue_id": str(uuid.uuid4()),
        "repository": "rozkalnsandris/example",
        "repository_id": 123456,
        "owner_user_id": 277435981,
        "shared_contract_sha": "1" * 40,
        "activation_main_sha": "2" * 40,
        "consumer_rules_digest_sha256": "3" * 64,
        "scope_digest_algorithm": mod.SCOPE_ALGORITHM,
        "authority": {
            "source": True,
            "merge": True,
            "live": False,
        },
        "issues": [
            {
                "number": 10,
                "node_id": "I_example_10",
                "scope_digest_sha256": digest_for(10),
            },
            {
                "number": 20,
                "node_id": "I_example_20",
                "scope_digest_sha256": digest_for(20),
            },
        ],
    }


class QueueBatchAuthorizationTests(unittest.TestCase):
    def test_valid_payload_passes(self):
        self.assertEqual(mod.validate_payload(valid_payload()), [])

    def test_queue_bounds_and_duplicates_fail_closed(self):
        payload = valid_payload()
        payload["issues"] = []
        self.assertIn("issues length must be between 1 and 10", mod.validate_payload(payload))

        payload = valid_payload()
        payload["issues"][1]["number"] = 10
        self.assertIn("duplicate issue number", mod.validate_payload(payload))

    def test_queue_never_grants_live(self):
        payload = valid_payload()
        payload["authority"]["live"] = True
        self.assertIn("LIVE authority must be false", mod.validate_payload(payload))

    def test_source_and_merge_authority_are_explicit(self):
        for key in ("source", "merge"):
            payload = valid_payload()
            payload["authority"][key] = False
            self.assertTrue(mod.validate_payload(payload))

    def test_only_active_frozen_issue_may_consume_authority(self):
        payload = valid_payload()
        self.assertTrue(mod.may_consume_item_authority(
            payload, active_issue=10, requested_issue=10
        ))
        self.assertFalse(mod.may_consume_item_authority(
            payload, active_issue=10, requested_issue=20
        ))
        self.assertFalse(mod.may_consume_item_authority(
            payload, active_issue=10, requested_issue=30
        ))

    def test_scope_digest_is_deterministic_and_sensitive(self):
        first = mod.canonical_scope_digest(
            "rozkalnsandris/example", 10, "Issue", "Body"
        )
        same = mod.canonical_scope_digest(
            "rozkalnsandris/example", 10, "Issue", "Body"
        )
        changed = mod.canonical_scope_digest(
            "rozkalnsandris/example", 10, "Issue", "Body changed"
        )
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)

    def test_frozen_issue_scope_and_identity_are_revalidated(self):
        payload = valid_payload()
        self.assertEqual(mod.verify_frozen_issue(
            payload,
            issue_number=10,
            node_id="I_example_10",
            current_title="Issue",
            current_body="Do the bounded thing",
        ), [])

        self.assertIn("issue scope digest drift", mod.verify_frozen_issue(
            payload,
            issue_number=10,
            node_id="I_example_10",
            current_title="Issue",
            current_body="Expanded scope",
        ))

        self.assertIn("issue node identity drift", mod.verify_frozen_issue(
            payload,
            issue_number=10,
            node_id="different-node",
            current_title="Issue",
            current_body="Do the bounded thing",
        ))

    def test_authorization_surface_must_be_owner_created_and_immutable(self):
        payload = valid_payload()
        meta = mod.SurfaceMetadata(
            title=mod.TITLE_PREFIX + payload["queue_id"],
            creator_user_id=277435981,
            configured_owner_user_id=277435981,
            created_at="2026-09-09T19:00:00+02:00",
            updated_at="2026-09-09T19:00:00+02:00",
        )
        self.assertEqual(mod.validate_surface(meta, payload), [])

        edited = mod.SurfaceMetadata(
            title=meta.title,
            creator_user_id=meta.creator_user_id,
            configured_owner_user_id=meta.configured_owner_user_id,
            created_at=meta.created_at,
            updated_at="2026-09-09T19:01:00+02:00",
        )
        self.assertIn(
            "authorization issue body or metadata was edited after creation",
            mod.validate_surface(edited, payload),
        )

        wrong_owner = mod.SurfaceMetadata(
            title=meta.title,
            creator_user_id=1,
            configured_owner_user_id=277435981,
            created_at=meta.created_at,
            updated_at=meta.updated_at,
        )
        self.assertIn(
            "controller issue creator must match configured owner",
            mod.validate_surface(wrong_owner, payload),
        )

    def test_title_binds_queue_identity(self):
        payload = valid_payload()
        meta = mod.SurfaceMetadata(
            title=mod.TITLE_PREFIX + str(uuid.uuid4()),
            creator_user_id=277435981,
            configured_owner_user_id=277435981,
            created_at="same",
            updated_at="same",
        )
        self.assertIn("controller issue title must bind queue_id", mod.validate_surface(meta, payload))

    def test_merge_gate_requires_exact_head_ci_reviews_scope_and_rules(self):
        payload = valid_payload()
        head = "a" * 40
        self.assertEqual(mod.merge_gate(
            payload,
            active_issue=10,
            requested_issue=10,
            expected_head_sha=head,
            observed_head_sha=head,
            exact_head_ci_pass=True,
            reviews_pass=True,
            scope_matches=True,
            rules_match=True,
        ), [])

        errors = mod.merge_gate(
            payload,
            active_issue=10,
            requested_issue=20,
            expected_head_sha=head,
            observed_head_sha="b" * 40,
            exact_head_ci_pass=False,
            reviews_pass=False,
            scope_matches=False,
            rules_match=False,
        )
        self.assertIn("requested issue may not consume Queue merge authority", errors)
        self.assertIn("exact PR head drift", errors)
        self.assertIn("exact-head CI is not proven PASS", errors)
        self.assertIn("review/thread gate is not proven PASS", errors)
        self.assertIn("frozen scope is not proven unchanged", errors)
        self.assertIn("repository rules boundary is not proven unchanged", errors)

    def test_policy_keeps_a3_non_active_but_defines_future_batch_authority(self):
        policy = json.loads(
            (ROOT / "policy" / "auto-run-full-queue-authorization-v1.json").read_text()
        )
        self.assertEqual(policy["status"], "A3_SHARED_BATCH_AUTHORIZATION_CONTRACT_NOT_ACTIVE")
        self.assertFalse(policy["activation"]["queue_command_active_in_consumers"])
        self.assertTrue(policy["activation"]["legacy_auto_run_full_remains_authoritative_until_adoption"])
        self.assertTrue(policy["authority"]["future_adopted_queue_activation_grants_source_authority_for_all_frozen_items"])
        self.assertTrue(policy["authority"]["future_adopted_queue_activation_grants_merge_authority_for_all_frozen_items"])
        self.assertTrue(policy["authority"]["authority_is_dormant_until_item_becomes_active"])
        self.assertFalse(policy["authority"]["queue_authorizes_live"])

    def test_schema_and_validator_field_sets_match(self):
        schema = json.loads(
            (ROOT / "policy" / "schemas" / "auto-run-full-queue-authorization-v1.schema.json").read_text()
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), mod.PAYLOAD_FIELDS)
        self.assertEqual(set(schema["properties"]), mod.PAYLOAD_FIELDS)
        self.assertEqual(schema["properties"]["schema"]["const"], mod.SCHEMA)
        self.assertEqual(
            schema["properties"]["scope_digest_algorithm"]["const"],
            mod.SCOPE_ALGORITHM,
        )
        issue_schema = schema["properties"]["issues"]["items"]
        self.assertEqual(set(issue_schema["required"]), mod.ISSUE_FIELDS)
        self.assertEqual(set(issue_schema["properties"]), mod.ISSUE_FIELDS)

    def test_normative_doc_states_no_live_and_no_consumer_activation(self):
        text = (
            ROOT / "docs" / "AUTO_RUN_FULL_QUEUE_AUTHORIZATION_V1.md"
        ).read_text().lower()
        self.assertIn("queue authority is never live authority", text)
        self.assertIn("a3 does not activate this command in any repository", text)
        self.assertIn("no separate owner `merge` command is required", text)
        self.assertIn("authorization body must not be edited after creation", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
