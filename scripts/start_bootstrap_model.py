from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

DEFAULT_PRECEDENCE = (
    "explicit_current_handoff",
    "active_focused_pr_blocking_current_phase",
    "active_issue_declared_as_current",
    "deploy_queue_source_reconciliation",
    "explicitly_ordered_next_roadmap_item",
)

FINAL_STATES = {
    "READY_FOR_MERGE",
    "PARKED",
    "STOP_ERROR",
    "NEW_SCOPE_OR_RISK",
    "AMBIGUOUS_CANONICAL_LANE",
    "IDLE",
}


@dataclass(frozen=True)
class Candidate:
    kind: str
    candidate_id: str
    phase_priority: int | None = None
    dependency_order: int | None = None
    labels: tuple[str, ...] = ()
    eligible: bool = True


def _tie_key(candidate: Candidate) -> tuple[int, int]:
    phase = candidate.phase_priority if candidate.phase_priority is not None else 2**31 - 1
    dependency = candidate.dependency_order if candidate.dependency_order is not None else 2**31 - 1
    return phase, dependency


def select_canonical_lane(
    candidates: Iterable[Candidate],
    *,
    precedence: Sequence[str] = DEFAULT_PRECEDENCE,
    excluded_labels: Iterable[str] = (),
) -> tuple[str | None, str]:
    ranks = {kind: index for index, kind in enumerate(precedence)}
    excluded = set(excluded_labels)
    eligible = [
        candidate
        for candidate in candidates
        if candidate.eligible
        and candidate.kind in ranks
        and not excluded.intersection(candidate.labels)
    ]
    if not eligible:
        return None, "IDLE"

    best_rank = min(ranks[candidate.kind] for candidate in eligible)
    same_class = [candidate for candidate in eligible if ranks[candidate.kind] == best_rank]
    best_key = min(_tie_key(candidate) for candidate in same_class)
    winners = [candidate for candidate in same_class if _tie_key(candidate) == best_key]

    if len(winners) != 1:
        return None, "AMBIGUOUS_CANONICAL_LANE"
    return winners[0].candidate_id, "SELECTED"


def route_final_state(
    *,
    source_error: bool = False,
    new_scope_or_risk: bool = False,
    merge_ready: bool = False,
    deferred_ready: bool = False,
    ambiguous_lane: bool = False,
    canonical_work_exists: bool = True,
) -> str:
    if source_error:
        return "STOP_ERROR"
    if new_scope_or_risk:
        return "NEW_SCOPE_OR_RISK"
    if ambiguous_lane:
        return "AMBIGUOUS_CANONICAL_LANE"
    if merge_ready:
        return "READY_FOR_MERGE"
    if deferred_ready:
        return "PARKED"
    if not canonical_work_exists:
        return "IDLE"
    raise ValueError("non-terminal state: safe canonical source work remains")


def validate_ready_dependency_graph(items: Sequence[Mapping[str, object]]) -> tuple[bool, str]:
    ready = {int(item["issue"]): item for item in items if item.get("state") == "READY"}
    graph: dict[int, list[int]] = {}
    for issue, item in ready.items():
        deps = [int(dep) for dep in item.get("dependencies", [])]
        graph[issue] = [dep for dep in deps if dep in ready]

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(node: int) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        for dep in graph.get(node, []):
            if not visit(dep):
                return False
        visiting.remove(node)
        visited.add(node)
        return True

    for node in graph:
        if not visit(node):
            return False, "DEPENDENCY_CYCLE"

    by_target: dict[str, list[int]] = {}
    for issue, item in ready.items():
        by_target.setdefault(str(item["target"]), []).append(issue)

    def depends_on(start: int, target: int, seen: set[int] | None = None) -> bool:
        seen = set() if seen is None else seen
        if start in seen:
            return False
        seen.add(start)
        for dep in graph.get(start, []):
            if dep == target or depends_on(dep, target, seen):
                return True
        return False

    for issues in by_target.values():
        if len(issues) < 2:
            continue
        for index, left in enumerate(issues):
            for right in issues[index + 1:]:
                if not depends_on(left, right) and not depends_on(right, left):
                    return False, "UNORDERED_SAME_TARGET"

    return True, "OK"
