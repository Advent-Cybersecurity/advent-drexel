#!/usr/bin/env python3
"""Recompute sealed Qwen3 structural-case answers from question text."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


PATTERNS = [
    re.compile(r"A club has (\d+) badges and receives (\d+) packs of (\d+) badges\. It gives away half its current badges, then receives (\d+) more\. How many badges does it have\?"),
    re.compile(r"A library receives (\d+) cartons with (\d+) cards each\. It discards (\d+) cards and shares the rest equally among (\d+) desks\. How many cards does each desk get\?"),
    re.compile(r"A shop starts with (\d+) tickets\. It doubles its supply, uses (\d+), triples what remains, then prints (\d+) more\. How many tickets are there now\?"),
    re.compile(r"A store has (\d+) pencils\. It gives away one third, then gets (\d+) boxes with (\d+) pencils in each box, then uses (\d+)\. How many pencils remain\?"),
]
STATE = re.compile(
    r"Three reading rooms have (\d+), (\d+), and (\d+) books in (\w+), (\w+), and (\w+), respectively\. "
    r"In order, (\w+) sends (\d+) books to (\w+); (\w+) sends half of its then-current books to (\w+); "
    r"(\w+) sends one third of its then-current books to (\w+); (\w+) lends out (\d+) books\. "
    r"How many books are in (\w+) at the end\?"
)
STATE_TOPOLOGIES = (
    (0, 1, 1, 0, 0, 2, 2, 0),
    (2, 0, 0, 1, 1, 0, 0, 2),
    (1, 2, 2, 1, 1, 0, 0, 1),
    (0, 2, 2, 1, 1, 2, 2, 0),
)


def answer(question):
    for variant, pattern in enumerate(PATTERNS):
        match = pattern.fullmatch(question)
        if not match:
            continue
        values = tuple(map(int, match.groups()))
        if variant == 0:
            start, packs, each, extra = values
            assert (start + packs * each) % 2 == 0
            return (start + packs * each) // 2 + extra, f"heldout-arithmetic-{variant}"
        if variant == 1:
            cartons, each, discarded, desks = values
            assert (cartons * each - discarded) % desks == 0
            return (cartons * each - discarded) // desks, f"heldout-arithmetic-{variant}"
        if variant == 2:
            start, used, added = values
            return (2 * start - used) * 3 + added, f"heldout-arithmetic-{variant}"
        start, boxes, each, used = values
        assert start % 3 == 0
        return start - start // 3 + boxes * each - used, f"heldout-arithmetic-{variant}"
    match = STATE.fullmatch(question)
    if not match:
        raise ValueError(f"unrecognized question: {question}")
    g = match.groups()
    names = g[3:6]
    assert len(set(names)) == 3
    state = dict(zip(names, map(int, g[0:3])))
    state[g[6]] -= int(g[7])
    state[g[8]] += int(g[7])
    assert state[g[9]] % 2 == 0
    moved = state[g[9]] // 2
    state[g[9]] -= moved
    state[g[10]] += moved
    assert state[g[11]] % 3 == 0
    moved = state[g[11]] // 3
    state[g[11]] -= moved
    state[g[12]] += moved
    state[g[13]] -= int(g[14])
    assert min(state.values()) >= 0
    topology = tuple(names.index(g[index]) for index in (6, 8, 9, 10, 11, 12, 13, 15))
    assert topology in STATE_TOPOLOGIES
    return state[g[15]], f"heldout-state-{STATE_TOPOLOGIES.index(topology)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--development", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    development = json.loads(args.development.read_text())
    assert manifest["kind"] == "evaluation"
    assert len(manifest["cases"]) == 2 * manifest["per_family"]
    dev_hashes = {case["question_sha256"] for case in development["cases"]}
    counts = Counter()
    hashes = set()
    for case in manifest["cases"]:
        digest = hashlib.sha256(case["question"].encode()).hexdigest()
        assert case["question_sha256"] == digest
        assert digest not in hashes and digest not in dev_hashes
        hashes.add(digest)
        expected, structure = answer(case["question"])
        assert expected == case["gold"], case["id"]
        assert case["structure"] == structure
        counts[case["structure"]] += 1
    assert len(counts) == 8
    assert set(counts.values()) == {manifest["per_family"] // 4}
    print(json.dumps({"manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                      "validated_cases": len(hashes), "structure_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
