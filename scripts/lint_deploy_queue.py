from __future__ import annotations

import argparse
import re
import sys

OPEN_STATES = {"WAITING", "READY", "BLOCKED", "EXECUTING", "STOP_ERROR"}
FORBIDDEN_TITLE_STATES = {"PARKED", "DONE", "CANCELLED"}
SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
REQUIRED_SECTIONS = (
    "source",
    "target",
    "execution",
    "entrypoint",
    "preflight",
    "verification",
    "mutation",
    "exclusion",
    "dependenc",
)


def lint(title: str, body: str) -> list[str]:
    errors: list[str] = []
    match = re.match(r"^\[DEPLOY-QUEUE\]\[([A-Z_]+)\]\s+.+", title)
    if not match:
        return ["queue title must match [DEPLOY-QUEUE][STATE] description"]
    state = match.group(1)
    if state in FORBIDDEN_TITLE_STATES:
        errors.append(f"{state} is not an open deploy-queue state")
    elif state not in OPEN_STATES:
        errors.append(f"unknown deploy-queue state: {state}")

    lower = body.lower()
    for marker in REQUIRED_SECTIONS:
        if marker not in lower:
            errors.append(f"queue body missing required contract marker: {marker}")

    if state == "READY":
        if not SHA40.search(body):
            errors.append("READY queue item must bind at least one exact 40-character SHA")
        if "ready" not in lower or ("authorization" not in lower and "authorize" not in lower):
            errors.append("READY queue item must state that readiness is not execution authorization")

    if state == "BLOCKED" and "reason" not in lower:
        errors.append("BLOCKED queue item must record a blocked reason")

    if "parked" in title.lower():
        errors.append("PARKED belongs to session UX, never the queue title")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args()
    body = open(args.body_file, encoding="utf-8").read()
    errors = lint(args.title, body)
    if errors:
        print("DEPLOY_QUEUE_LINT=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DEPLOY_QUEUE_LINT=PASS")
    print("MUTATION=NO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
