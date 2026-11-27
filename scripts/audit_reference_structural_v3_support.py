#!/usr/bin/env python3
"""Public V3 structural-ID collision audit; never scores a model or seals cases."""

import collections
import hashlib
import json
import random
from pathlib import Path

from calibrate_reference_structural_quality_v3 import arithmetic_case, state_case


SEED = 83791
N_PER_CELL = 10000
RUNNER = Path(__file__).with_name("calibrate_reference_structural_quality_v3.py")
OUTPUT = Path(__file__).resolve().parent.parent / "data/frontier-quality-reference-structural-v3-support-audit-2026-11-13.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rng = random.Random(SEED)
    cells = []
    for family, maker in (("arithmetic", arithmetic_case), ("state", state_case)):
        for length in (4, 7):
            ids = []
            invalid = 0
            while len(ids) < N_PER_CELL:
                try:
                    case = maker(rng, 1, length)
                except AssertionError:
                    invalid += 1
                    continue
                ids.append(case["structure_id"])
            counts = collections.Counter(ids)
            cells.append({"family": family, "event_count": length,
                          "valid_draws": len(ids), "invalid_rejections": invalid,
                          "unique_ids": len(counts),
                          "matching_id_pairs": sum(v * (v - 1) // 2 for v in counts.values()),
                          "max_repeats_of_one_id": max(counts.values())})
    audit = {"kind": "public_v3_structure_signature_support_audit",
             "seed": SEED, "valid_draws_per_cell": N_PER_CELL,
             "runner_sha256_at_audit": sha(RUNNER),
             "arithmetic_four_event_exact_signature_support": 216,
             "arithmetic_four_event_support_derivation":
             "12 valid permutations of reserve/release/conditional/consume, times 3 reserve divisors, times 3 release divisors, times 2 conditional branches",
             "caveat": "IDs encode selected event features, not proven end-to-end functional equivalence; counts do not certify a future sealed grammar",
             "cells": cells}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"{OUTPUT}: sha256={sha(OUTPUT)}")
    for cell in cells:
        print(cell)


if __name__ == "__main__":
    main()
