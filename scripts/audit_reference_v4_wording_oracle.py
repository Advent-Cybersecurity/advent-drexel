#!/usr/bin/env python3
"""Reconstruct public V4 state cases from wording and independently replay them.

This audit reads only the public reference development manifest. It never
connects to a model or reads a sealed test.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOMS = "ABCD"
HEADER = re.compile(
    r"Four storage rooms start with (\d+) items in room A, "
    r"(\d+) items in room B, (\d+) items in room C, "
    r"(\d+) items in room D\. In the following order, "
)
TAIL = re.compile(r"\. How many items are in room ([ABCD]) at the end\?\Z")
FRACTION = re.compile(
    r"room ([ABCD]) sends one item for every complete group of (\d+) "
    r"items it holds at that point to room ([ABCD]), rounding down\Z"
)
FIXED = re.compile(r"room ([ABCD]) sends (\d+) items to room ([ABCD])\Z")
CONDITIONAL = re.compile(
    r"if room ([ABCD]) holds at least (\d+) items at that point, "
    r"room ([ABCD]) sends (\d+) items to room ([ABCD]); otherwise "
    r"room ([ABCD]) sends (\d+) items to room ([ABCD])\Z"
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_question(question):
    header = HEADER.match(question)
    tail = TAIL.search(question)
    if not header or not tail:
        raise ValueError("header or query does not match grammar")
    initial = dict(zip(ROOMS, map(int, header.groups())))
    target = tail.group(1)
    sentences = question[header.end():tail.start()].split("; then ")
    events = []
    for sentence in sentences:
        conditional = CONDITIONAL.fullmatch(sentence)
        fraction = FRACTION.fullmatch(sentence)
        fixed = FIXED.fullmatch(sentence)
        if sum(match is not None for match in (conditional, fraction, fixed)) != 1:
            raise ValueError(f"unrecognized or ambiguous event: {sentence}")
        if conditional:
            name, threshold, high_source, high_amount, high_dest, low_source, low_amount, low_dest = conditional.groups()
            if name != high_source or name != low_dest or high_dest != low_source:
                raise ValueError(f"conditional directions inconsistent: {sentence}")
            if high_amount != low_amount:
                raise ValueError(f"conditional amounts differ: {sentence}")
            events.append({"op": "conditional", "source": name,
                           "destination": high_dest, "threshold": int(threshold),
                           "amount": int(high_amount)})
        elif fraction:
            source, divisor, destination = fraction.groups()
            events.append({"op": "fraction", "source": source,
                           "destination": destination, "divisor": int(divisor)})
        else:
            source, amount, destination = fixed.groups()
            events.append({"op": "fixed", "source": source,
                           "destination": destination, "amount": int(amount)})
    return initial, events, target


def replay(initial, events):
    balance = initial.copy()
    trace = []
    branches = []
    for event in events:
        source = event["source"]
        destination = event["destination"]
        if event["op"] == "conditional":
            high = balance[source] >= event["threshold"]
            branches.append("high" if high else "low")
            if not high:
                source, destination = destination, source
            amount = event["amount"]
        elif event["op"] == "fraction":
            amount = balance[source] // event["divisor"]
        else:
            amount = event["amount"]
        if source == destination or amount < 0 or amount > balance[source]:
            raise ValueError("invalid transfer")
        balance[source] -= amount
        balance[destination] += amount
        trace.append([balance[name] for name in ROOMS])
        if sum(balance.values()) != sum(initial.values()):
            raise ValueError("conservation invariant failed")
    return balance, trace, branches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("kind") != "reference_only_public_development" or manifest.get("schema_version") != 4:
        raise ValueError("expected public V4 reference development manifest")
    rows = []
    for case in manifest["cases"]:
        initial, parsed, target = parse_question(case["question"])
        final, trace, branches = replay(initial, parsed)
        stored = [{key: value for key, value in event.items() if key != "branch"}
                  for event in case["events"]]
        branch_stored = [event["branch"] for event in case["events"]
                         if event["op"] == "conditional"]
        checks = {
            "initial": initial == case["initial"],
            "events": parsed == stored,
            "target": target == case["target"],
            "final": final == case["final"],
            "trace": trace == case["trace"],
            "gold": final[target] == case["gold"],
            "branches": branches == branch_stored,
            "length": len(parsed) == case["length"],
            "question_sha256": hashlib.sha256(case["question"].encode()).hexdigest()
                               == case["question_sha256"],
        }
        rows.append({"id": case["id"], "length": case["length"],
                     "branch": branches, "checks": checks})
    failures = [{"id": row["id"], "checks": [name for name, ok in row["checks"].items() if not ok]}
                for row in rows if not all(row["checks"].values())]
    result = {
        "kind": "public_v4_reference_wording_oracle_audit",
        "manifest_sha256": sha256(args.manifest),
        "scope": "Exact text parsing and separate state replay for the 12 public V4 cases; mechanical audit only, not independent human interpretation.",
        "case_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "branch_histogram": dict(sorted(Counter(branch for row in rows for branch in row["branch"]).items())),
        "by_length": {str(length): dict(sorted(Counter(branch for row in rows
                                             if row["length"] == length
                                             for branch in row["branch"]).items()))
                      for length in sorted({row["length"] for row in rows})},
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={sha256(args.output)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
