#!/usr/bin/env python3
"""Audit which V3 state-transfer events can affect the queried final balance.

This is a public development audit. It does not query any model or sealed case.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state_ancestors(case):
    needed = {case["target"]}
    relevant = []
    for position, event in reversed(list(enumerate(case["events"], start=1))):
        source = event["source"]
        destination = event["destination"]
        if source not in needed and destination not in needed:
            continue
        relevant.append(position)
        # Fractional destination updates depend on the source balance.
        # Conditional updates to either room depend on the source balance.
        if event["op"] == "fraction" and destination in needed:
            needed.add(source)
        elif event["op"] == "conditional":
            needed.add(source)
    return sorted(relevant), sorted(needed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("kind") != "reference_only_public_development":
        raise ValueError("not a public development manifest")
    rows = []
    for case in manifest["cases"]:
        if case["family"] != "state":
            continue
        positions, initial_rooms = state_ancestors(case)
        rows.append({"id": case["id"], "event_count": case["length"],
                     "relevant_event_positions": positions,
                     "relevant_event_count": len(positions),
                     "needed_initial_rooms": initial_rooms})
    by_length = {}
    for length in sorted({row["event_count"] for row in rows}):
        group = [row for row in rows if row["event_count"] == length]
        by_length[str(length)] = {
            "cases": len(group),
            "relevant_event_count_histogram": dict(sorted(Counter(
                row["relevant_event_count"] for row in group).items())),
            "all_events_relevant": sum(row["relevant_event_count"] == length for row in group),
        }
    result = {"kind": "public_v3_state_query_ancestor_audit",
              "manifest_sha256": digest(args.manifest),
              "rule": "Backward numeric-state dependency from the queried final room; fixed transfers do not introduce dependence on the other room's initial balance; conditional direction depends on its named source balance.",
              "caveat": "Counts omit feasibility constraints and do not establish functional-equivalence classes or model difficulty.",
              "by_length": by_length, "cases": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
