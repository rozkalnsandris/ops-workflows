from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

POLICY = "GITHUB-ONLY / LIVE-ALL v1"
START = "START GITHUB-ONLY v1"
ADOPTION = "2026-08-25.2"
INVARIANTS = {
    "start_step_count": 10,
    "open_issue_required": False,
    "invent_speculative_work_when_idle": False,
    "unresolved_tie_result": "AMBIGUOUS_CANONICAL_LANE",
    "parked_is_queue_state": False,
    "executor_capability_affects_readiness": False,
    "executor_unavailable_alone_is_blocked": False,
    "merge_requires_explicit_owner_authorization": True,
    "auto_merge": False,
    "direct_default_branch_content_writes": False,
    "live_mutation_allowed_under_github_only": False,
    "no_executable_live_all_consumes_authorization": False,
}
AGENT_MARKERS = ("START_GITHUB_ONLY_V1", "PARKED", "EXECUTOR", "READY", "BLOCKED")


def load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def check(ok: bool, message: str, errors: list[str]) -> None:
    if not ok:
        errors.append(message)


def manifest_checks(m: dict, p: dict, errors: list[str]) -> None:
    check(m.get("schema_version") == 1, "manifest schema_version != 1", errors)
    check(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(m.get("repository", ""))) is not None,
          "manifest repository must be owner/name", errors)
    shared = m.get("shared_policy", {})
    check(shared.get("repository") == "rozkalnsandris/ops-workflows", "manifest canonical repository mismatch", errors)
    check(shared.get("contract") == POLICY and shared.get("startup_contract") == START, "manifest contract mismatch", errors)
    check(shared.get("minimum_machine_schema", 0) <= p.get("schema_version", 0), "manifest requires newer machine schema", errors)
    check(shared.get("adoption_version") == p.get("adoption_version"), "manifest adoption drift", errors)
    check(m.get("authority", {}).get("local_rules_override_when_stricter") is True, "stricter local rules must win", errors)
    cont = m.get("continuation", {})
    precedence = cont.get("precedence", [])
    check(bool(precedence) and len(precedence) == len(set(precedence)), "continuation precedence must be unique/non-empty", errors)
    check(cont.get("unresolved_tie_result") == "AMBIGUOUS_CANONICAL_LANE", "unresolved tie must fail closed", errors)
    check(cont.get("no_candidate_result") == "IDLE", "no candidate must route IDLE", errors)
    src = m.get("source_work", {})
    check(src.get("default_branch_direct_writes") is False, "direct default-branch writes must be false", errors)
    check(src.get("bounded_correction_limit") in (0, 1, 2), "bounded correction limit must be <=2", errors)
    check(src.get("jit_revalidation") is True, "JIT revalidation required", errors)
    merge = m.get("merge", {})
    for key, expected in {
        "method": "squash", "explicit_owner_authorization": True, "bind_expected_head_sha": True,
        "require_current_head_revalidation": True, "require_exact_head_ci": True, "auto_merge": False,
    }.items():
        check(merge.get(key) == expected, f"manifest merge invariant mismatch: {key}", errors)
    dep = m.get("deploy", {})
    check(dep.get("queue_repository") == "rozkalnsandris/ops-workflows", "manifest queue repository mismatch", errors)
    check(dep.get("executor_capability_affects_readiness") is False, "executor capability must not affect READY", errors)


def snapshot_checks(snapshot: dict, p: dict, errors: list[str]) -> None:
    check(snapshot.get("policy") == POLICY, "snapshot policy mismatch", errors)
    check(snapshot.get("canonical_repository") == "rozkalnsandris/ops-workflows", "snapshot canonical repository mismatch", errors)
    check(snapshot.get("startup_contract") == START, "snapshot START contract mismatch", errors)
    check(snapshot.get("adoption_version") == p.get("adoption_version"), "snapshot adoption drift", errors)
    values = snapshot.get("invariants", {})
    for key, expected in INVARIANTS.items():
        check(values.get(key) == expected, f"snapshot invariant mismatch: {key}", errors)


def canonical(root: Path) -> list[str]:
    errors: list[str] = []
    p = load(root / "policy/github-only-live-all-v1.json")
    m = load(root / ".github/start-github-only.json")
    snapshot = load(root / "policy/github-only-consumer-baseline.json")
    live = load(root / "policy/live-entrypoints-v1.json")
    executors = load(root / "policy/executor-capabilities-v1.json")
    check(p.get("schema_version") == 2 and p.get("policy") == POLICY, "canonical policy identity mismatch", errors)
    check(p.get("adoption_version") == ADOPTION, "canonical adoption version mismatch", errors)
    gh = p.get("commands", {}).get("github_only", {})
    boot = gh.get("start_bootstrap", {})
    for key, expected in {
        "deterministic": True, "step_count": 10, "open_issue_required": False,
        "invent_speculative_work_when_idle": False,
        "jit_revalidation_before_state_dependent_github_mutation": True,
    }.items():
        check(boot.get(key) == expected, f"START invariant mismatch: {key}", errors)
    check(gh.get("continuation", {}).get("unresolved_tie_result") == "AMBIGUOUS_CANONICAL_LANE", "tie result mismatch", errors)
    check(gh.get("parked_session", {}).get("is_queue_state") is False, "PARKED must not be queue state", errors)
    check("DIRECT_DEFAULT_BRANCH_CONTENT_WRITE" in gh.get("forbids", []), "direct default-branch write prohibition missing", errors)
    q = p.get("queue", {})
    check("PARKED" not in q.get("open_queue_states", []) and "DONE" not in q.get("open_queue_states", []),
          "session/terminal states leaked into open queue states", errors)
    check(q.get("terminal_outcomes") == ["DONE", "CANCELLED"], "terminal outcomes mismatch", errors)
    check(q.get("executor_unavailable_alone_must_not_change_ready_to_blocked") is True, "READY/PARKED invariant mismatch", errors)
    check(q.get("dependency_graph_must_be_acyclic") is True and q.get("same_target_requires_explicit_order") is True,
          "queue DAG/conflict invariants missing", errors)
    text = (root / "docs/START_GITHUB_ONLY_V1.md").read_text(encoding="utf-8")
    check("**Status:** Accepted" in text and "## 5. Final-state router" in text, "START document authority/router mismatch", errors)
    manifest_checks(m, p, errors)
    snapshot_checks(snapshot, p, errors)
    entry = [e for e in live.get("entries", []) if e.get("repository") == "rozkalnsandris/RPi5_main" and e.get("id") == "deals-9128-route-cutover"]
    check(len(entry) == 1, "RPi5 special live entrypoint missing", errors)
    if entry:
        e = entry[0]
        check(e.get("authorization_class") == "SPECIAL_COMPOSITE_LIVE", "RPi5 authorization class mismatch", errors)
        check(e.get("operations", {}).get("cutover", {}).get("mutation") is True, "RPi5 cutover classification mismatch", errors)
        check("cutover" in e.get("github_only", {}).get("forbidden_operations", []), "GITHUB-ONLY must forbid RPi5 cutover", errors)
    emap = {e.get("executor_class"): e for e in executors.get("executors", [])}
    for cls in ("github-hosted", "trusted-home-host", "repository-defined-trusted-executor"):
        check(cls in emap, f"executor contract missing: {cls}", errors)
        if cls in emap:
            check(emap[cls].get("capability_probe", {}).get("mutation_allowed") is False, f"executor probe mutating: {cls}", errors)
    managed = (root / "policy/managed/GITHUB_ONLY_START_V1.md").read_text(encoding="utf-8").upper()
    for marker in AGENT_MARKERS + ("AMBIGUOUS_CANONICAL_LANE", "NO ACTION REQUIRED NOW"):
        check(marker in managed, f"managed block marker missing: {marker}", errors)
    for path in (
        "policy/schemas/start-github-only-v1.schema.json", "policy/schemas/live-entrypoints-v1.schema.json",
        ".github/workflows/github-only-policy-drift.yml", ".github/workflows/github-only-queue-lint.yml",
        "scripts/start_bootstrap_model.py", "tests/start_bootstrap/test_conformance.py",
    ):
        check((root / path).is_file(), f"enforcement file missing: {path}", errors)
    return errors


def consumer(canonical_root: Path, consumer_root: Path, manifest_path: str, snapshot_path: str) -> list[str]:
    errors: list[str] = []
    p = load(canonical_root / "policy/github-only-live-all-v1.json")
    manifest_checks(load(consumer_root / manifest_path), p, errors)
    snapshot_checks(load(consumer_root / snapshot_path), p, errors)
    agents_path = consumer_root / "AGENTS.md"
    if not agents_path.is_file():
        errors.append("consumer AGENTS.md missing")
    else:
        agents = agents_path.read_text(encoding="utf-8")
        upper = agents.upper()
        for marker in AGENT_MARKERS:
            check(marker in upper, f"consumer AGENTS marker missing: {marker}", errors)
        check("no open issue" in agents.lower() or "absence of an open issue" in agents.lower(),
              "consumer AGENTS must state no-open-issue is non-terminal", errors)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--canonical-root")
    ap.add_argument("--consumer-root")
    ap.add_argument("--manifest", default=".github/start-github-only.json")
    ap.add_argument("--snapshot", default=".github/github-only-policy.json")
    a = ap.parse_args()
    try:
        errors = (consumer(Path(a.canonical_root or a.root).resolve(), Path(a.consumer_root).resolve(), a.manifest, a.snapshot)
                  if a.consumer_root else canonical(Path(a.root).resolve()))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    if errors:
        print("GITHUB_ONLY_POLICY=FAIL")
        print("\n".join(f"- {e}" for e in errors))
        return 1
    print("GITHUB_ONLY_POLICY=PASS")
    print("MUTATION=NO")
    return 0

if __name__ == "__main__":
    sys.exit(main())
