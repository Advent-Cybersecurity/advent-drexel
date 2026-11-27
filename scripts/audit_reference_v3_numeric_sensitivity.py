#!/usr/bin/env python3
"""Public V3 state-case leave-one-event-out sensitivity; no model use."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from audit_reference_v3_query_ancestors import state_ancestors
from calibrate_reference_structural_quality_v3 import state_replay


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(case):
    positions, _ = state_ancestors(case)
    relevant = set(positions)
    checks = []
    for index in range(len(case["events"])):
        trimmed = case["events"][:index] + case["events"][index + 1:]
        try:
            final, _ = state_replay(case["initial"], trimmed)
            answer = final[case["target"]]
            checks.append({"position": index + 1,
                           "symbolically_relevant": index + 1 in relevant,
                           "deleted_event_answer": answer,
                           "changes_answer": answer != case["gold"]})
        except AssertionError:
            checks.append({"position": index + 1,
                           "symbolically_relevant": index + 1 in relevant,
                           "invalid_replay": True})
    return {"id": case["id"], "event_count": len(case["events"]),
            "gold": case["gold"], "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("kind") != "reference_only_public_development":
        raise ValueError("not a public development manifest")
    cases = [assess(case) for case in manifest["cases"]
             if case["family"] == "state"]
    totals = Counter()
    for case in cases:
        for check in case["checks"]:
            relevant = check["symbolically_relevant"]
            if check.get("invalid_replay"):
                totals["relevant_invalid" if relevant else "irrelevant_invalid"] += 1
            elif check["changes_answer"]:
                totals["relevant_changed" if relevant else "irrelevant_changed"] += 1
            else:
                totals["relevant_unchanged" if relevant else "irrelevant_unchanged"] += 1
    result = {"kind": "public_v3_state_numeric_sensitivity_audit",
              "manifest_sha256": digest(args.manifest),
              "query_ancestor_audit_sha256": digest(Path(__file__).with_name(
                  "audit_reference_v3_query_ancestors.py")),
              "generator_sha256": digest(Path(__file__).with_name(
                  "calibrate_reference_structural_quality_v3.py")),
              "rule": "Delete one event and replay all later events from the same initial state; compare the queried final value with the frozen gold.",
              "caveat": "This finite-instance deletion diagnostic neither proves functional dependence nor preserves the originally sampled distribution. A zero change may reflect cancellation or integer rounding; an invalid replay has no answer comparison. No model or sealed case was queried.",
              "totals": dict(sorted(totals.items())), "cases": cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
