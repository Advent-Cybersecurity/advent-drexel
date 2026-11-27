#!/usr/bin/env python3
"""Explore sample size for the repository's two-family paired quality gate.

This is prospective scenario analysis, not an estimate of model performance.
Each simulated item has one of four paired outcomes. Families are simulated
independently for planning; the real evaluation must report its observed data.
"""

import argparse
import json

import numpy as np
from scipy.stats import beta

from run_generated_multistep_quality import BOUND_ALPHA, FLOOR, MARGIN


def lower(k, n, alpha):
    return np.where(k == 0, 0.0, beta.ppf(alpha, k, n - k + 1))


def upper(k, n, alpha):
    return np.where(k == n, 1.0, beta.ppf(1 - alpha, k + 1, n - k))


def family_pass(counts, n):
    both, ref_only, cand_only = counts[..., 0], counts[..., 1], counts[..., 2]
    ref_success = both + ref_only
    cand_success = both + cand_only
    ref_floor = lower(ref_success, n, BOUND_ALPHA) > FLOOR
    cand_floor = lower(cand_success, n, BOUND_ALPHA) > FLOOR
    paired = lower(cand_only, n, BOUND_ALPHA / 2) - upper(ref_only, n, BOUND_ALPHA / 2)
    return ref_floor & cand_floor & (paired > -MARGIN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, nargs="+", default=[300, 600, 900, 1200])
    parser.add_argument("--reference-rate", type=float, nargs="+", default=[0.7, 0.8])
    parser.add_argument("--discordance", type=float, nargs="+", default=[0.05, 0.1, 0.2])
    parser.add_argument("--trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261113)
    args = parser.parse_args()
    if any(n < 1 for n in args.n) or args.trials < 1:
        parser.error("n and trials must be positive")
    rng = np.random.default_rng(args.seed)
    rows = []
    for p in args.reference_rate:
        for d in args.discordance:
            if not (0 <= p <= 1 and 0 <= d <= 1 and d / 2 <= min(p, 1 - p)):
                parser.error("invalid rate/discordance combination")
            probabilities = [p - d / 2, d / 2, d / 2, 1 - p - d / 2]
            for n in args.n:
                counts = rng.multinomial(n, probabilities, size=(args.trials, 2))
                passed = family_pass(counts, n)
                joint_passes = int(np.count_nonzero(passed.all(axis=1)))
                rows.append({
                    "reference_and_candidate_true_rate": p,
                    "total_discordance_probability": d,
                    "n_per_family": n,
                    "responses_for_two_models_two_families": 4 * n,
                    "joint_passes": joint_passes,
                    "joint_pass_fraction": joint_passes / args.trials,
                    "family_pass_fraction": float(np.mean(passed)),
                })
    result = {
        "purpose": "prospective scenario analysis, not fitted power",
        "assumptions": "equal true arm rates, symmetric discordance, independent items and families",
        "seed": args.seed,
        "trials_per_scenario": args.trials,
        "gate": {"floor": FLOOR, "paired_margin": MARGIN,
                 "bonferroni_alpha_per_assertion": BOUND_ALPHA},
        "rows": rows,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
