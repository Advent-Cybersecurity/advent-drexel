#!/usr/bin/env python3
"""Audit public V4 state-generator support after its filters; no model use."""

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from audit_reference_v3_dependency_depth import longest_path
from audit_reference_v3_query_ancestors import state_ancestors
from audit_reference_v3_relevant_signature_support import canonical
from calibrate_reference_structural_quality_v3 import state_case
from calibrate_reference_structural_quality_v4 import every_event_changes_answer


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frequency_summary(counts):
    accepted = sum(counts.values())
    pairs = accepted * (accepted - 1) // 2
    matching = sum(count * (count - 1) // 2 for count in counts.values())
    return {
        "accepted": accepted,
        "unique": len(counts),
        "matching_pairs": matching,
        "all_pairs": pairs,
        "empirical_pair_collision_rate": matching / pairs if pairs else 0,
        "maximum_frequency": max(counts.values(), default=0),
    }


def assess(seed, draws, length, minimum_depth):
    rng = random.Random(seed + length)
    rejected = Counter()
    depths, branches = Counter(), Counter()
    topology = Counter()
    topology_with_divisor_and_branch = Counter()
    for index in range(draws):
        case = state_case(rng, index, length)
        depth = longest_path(case)
        if depth < minimum_depth:
            rejected["insufficient_depth"] += 1
            continue
        ancestors, _ = state_ancestors(case)
        if len(ancestors) != length:
            rejected["irrelevant_event"] += 1
            continue
        if not every_event_changes_answer(case):
            rejected["numerically_insensitive"] += 1
            continue
        events = [case["events"][i - 1] for i in ancestors]
        topology[canonical(events, case["target"], False, False)] += 1
        topology_with_divisor_and_branch[
            canonical(events, case["target"], True, True)
        ] += 1
        depths[depth] += 1
        branches[next(event["branch"] for event in case["events"]
                      if event["op"] == "conditional")] += 1
    return {
        "draws": draws,
        "minimum_depth": minimum_depth,
        "rejected": dict(sorted(rejected.items())),
        "depth_counts": dict(sorted(depths.items())),
        "conditional_branch_counts": dict(sorted(branches.items())),
        "operator_topology": frequency_summary(topology),
        "topology_with_divisor_and_realized_branch": frequency_summary(
            topology_with_divisor_and_branch),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=83793)
    parser.add_argument("--draws", type=int, default=10000)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = {
        "kind": "public_reference_only_generator_support_audit",
        "note": "Independent seeded draws before V4 uniqueness and V3-exclusion filtering. Syntactic signatures do not prove functional nonequivalence.",
        "seed": args.seed,
        "draws_per_length": args.draws,
        "generator_script_sha256": sha256(Path(__file__).with_name(
            "calibrate_reference_structural_quality_v3.py")),
        "v4_filter_script_sha256": sha256(Path(__file__).with_name(
            "calibrate_reference_structural_quality_v4.py")),
        "cells": {
            "7": assess(args.seed, args.draws, 7, 7),
            "9": assess(args.seed, args.draws, 9, 8),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(args.output)
    print(sha256(args.output))


if __name__ == "__main__":
    main()
