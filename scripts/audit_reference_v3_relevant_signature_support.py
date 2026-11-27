#!/usr/bin/env python3
"""Public V3 state-grammar signature granularity audit; no model use."""

import argparse
import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from audit_reference_v3_dependency_depth import longest_path
from audit_reference_v3_query_ancestors import state_ancestors
from calibrate_reference_structural_quality_v3 import ROOMS, state_case


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(events, target, keep_divisor, keep_branch):
    variants = []
    for names in itertools.permutations(ROOMS):
        mapping = dict(zip(ROOMS, names))
        signature = []
        for event in events:
            item = [event["op"], mapping[event["source"]],
                    mapping[event["destination"]]]
            if keep_divisor:
                item.append(event.get("divisor", 0))
            if keep_branch:
                item.append(event.get("branch", ""))
            signature.append(tuple(item))
        variants.append((tuple(signature), mapping[target]))
    return min(variants)


def summarize(counts):
    return {
        "unique": len(counts),
        "matching_pairs": sum(count * (count - 1) // 2
                              for count in counts.values()),
        "maximum_frequency": max(counts.values(), default=0),
    }


def assess(seed, draws, length):
    rng = random.Random(seed + length)
    accepted = Counter()
    signatures = {name: Counter() for name in (
        "full_program_with_divisor_and_realized_branch",
        "query_ancestors_with_divisor_and_realized_branch",
        "query_ancestors_with_realized_branch",
        "query_ancestor_operator_topology_only",
    )}
    for index in range(draws):
        case = state_case(rng, index, length)
        positions, _ = state_ancestors(case)
        depth = longest_path(case)
        minimum = 3 if length == 4 else 5
        if depth < minimum or len(positions) < minimum:
            continue
        accepted["count"] += 1
        query_events = [case["events"][position - 1]
                        for position in positions]
        specs = (
            ("full_program_with_divisor_and_realized_branch",
             case["events"], True, True),
            ("query_ancestors_with_divisor_and_realized_branch",
             query_events, True, True),
            ("query_ancestors_with_realized_branch",
             query_events, False, True),
            ("query_ancestor_operator_topology_only",
             query_events, False, False),
        )
        for name, events, divisor, branch in specs:
            signatures[name][canonical(events, case["target"],
                                       divisor, branch)] += 1
    return {"draws": draws, "accepted": accepted["count"],
            "signatures": {name: summarize(counter)
                           for name, counter in signatures.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=83792)
    parser.add_argument("--draws-per-cell", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    own = Path(__file__).parent
    result = {
        "kind": "public_v3_state_relevant_signature_support_audit",
        "seed": args.seed,
        "generator_sha256": digest(own / "calibrate_reference_structural_quality_v3.py"),
        "query_ancestor_audit_sha256": digest(own / "audit_reference_v3_query_ancestors.py"),
        "depth_audit_sha256": digest(own / "audit_reference_v3_dependency_depth.py"),
        "rule": "Four-event depth and ancestor count at least three; seven-event depth and ancestor count at least five; same seeded draws as the depth-yield audit.",
        "caveat": "Each level is a syntactic signature under room renaming. Matching signatures do not prove end-to-end functional equivalence; distinct signatures do not prove functional non-equivalence. Removing branch or divisor is an intentionally coarse topology view. No model or sealed case was queried.",
        "cells": {str(length): assess(args.seed, args.draws_per_cell, length)
                  for length in (4, 7)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
