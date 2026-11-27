#!/usr/bin/env python3
"""Public V3 state-case longest query-dependency path, with no model queries."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def longest_path(case):
    """Count event nodes on the longest symbolic path to the target room."""
    rooms = tuple(sorted(case["initial"]))
    depth = {name: 0 for name in rooms}
    for event in case["events"]:
        source, destination = event["source"], event["destination"]
        old = depth.copy()
        # A fixed transfer changes each affected room by a constant. A
        # fraction depends on the source balance; a conditional's direction
        # depends on its named source balance. This is symbolic dependence
        # over the declared domain, not observed numeric sensitivity.
        depth[source] = old[source] + 1
        if event["op"] in ("fraction", "conditional"):
            depth[destination] = 1 + max(old[source], old[destination])
        else:
            depth[destination] = old[destination] + 1
    return depth[case["target"]]


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
        rows.append({"id": case["id"], "event_count": case["length"],
                     "longest_query_dependency_path": longest_path(case)})
    by_length = {}
    for length in sorted({row["event_count"] for row in rows}):
        group = [row for row in rows if row["event_count"] == length]
        by_length[str(length)] = {
            "cases": len(group),
            "depth_histogram": dict(sorted(Counter(
                row["longest_query_dependency_path"] for row in group).items())),
            "full_length_depth": sum(row["longest_query_dependency_path"] == length
                                     for row in group),
        }
    result = {
        "kind": "public_v3_state_query_dependency_depth_audit",
        "manifest_sha256": sha256(args.manifest),
        "rule": "Longest symbolic event path to queried final room; fixed transfers each depend only on the same room's old balance, fraction transfers also depend on source balance, and conditional direction depends on its named source balance.",
        "caveat": "Symbolic path length does not prove numeric sensitivity on this instance, end-to-end functional non-equivalence, or model difficulty.",
        "by_length": by_length,
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={sha256(args.output)}")


if __name__ == "__main__":
    main()
