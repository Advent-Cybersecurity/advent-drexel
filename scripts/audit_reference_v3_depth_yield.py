#!/usr/bin/env python3
"""Public grammar yield under query-ancestry and path-depth rules; no model use."""

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from audit_reference_v3_dependency_depth import longest_path
from audit_reference_v3_query_ancestors import state_ancestors
from calibrate_reference_structural_quality_v3 import state_case


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(seed, draws, length):
    rng = random.Random(seed + length)
    depths = Counter()
    relevant_counts = Counter()
    accepted = Counter()
    signatures = Counter()
    for index in range(draws):
        case = state_case(rng, index, length)
        depth = longest_path(case)
        relevant = len(state_ancestors(case)[0])
        depths[depth] += 1
        relevant_counts[relevant] += 1
        if length == 4:
            keep = depth >= 3 and relevant >= 3
        else:
            keep = depth >= 5 and relevant >= 5
        if keep:
            accepted["count"] += 1
            signatures[case["structure_id"]] += 1
            if relevant == length:
                accepted["all_events_relevant"] += 1
            if depth == length:
                accepted["full_length_depth"] += 1
    return {
        "draws": draws,
        "rule": "depth >= 3 and relevant events >= 3" if length == 4 else
                "depth >= 5 and relevant events >= 5",
        "accepted": accepted["count"],
        "acceptance_fraction": accepted["count"] / draws,
        "accepted_all_events_relevant": accepted["all_events_relevant"],
        "accepted_full_length_depth": accepted["full_length_depth"],
        "unique_full_program_signatures_among_accepted": len(signatures),
        "matching_full_program_signature_pairs_among_accepted": sum(
            frequency * (frequency - 1) // 2 for frequency in signatures.values()),
        "maximum_signature_frequency_among_accepted": max(signatures.values(), default=0),
        "depth_histogram": dict(sorted(depths.items())),
        "relevant_event_histogram": dict(sorted(relevant_counts.items())),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=83792)
    parser.add_argument("--draws-per-cell", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = {
        "kind": "public_reference_v3_state_depth_yield_audit",
        "seed": args.seed,
        "generator_sha256": digest(Path(__file__).with_name(
            "calibrate_reference_structural_quality_v3.py")),
        "query_ancestor_audit_sha256": digest(Path(__file__).with_name(
            "audit_reference_v3_query_ancestors.py")),
        "depth_audit_sha256": digest(Path(__file__).with_name(
            "audit_reference_v3_dependency_depth.py")),
        "caveat": "Monte Carlo estimates of the public V3 grammar only; IDs encode full programs, not query-ancestor functional-equivalence classes. No candidate or sealed case was generated or queried.",
        "cells": {str(length): assess(args.seed, args.draws_per_cell, length)
                  for length in (4, 7)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
