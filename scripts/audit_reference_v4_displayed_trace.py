#!/usr/bin/env python3
"""Audit displayed V4 room assignments against the public oracle trace.

This checks only the two explicit arithmetic assignment lines under each
numbered step. It does not infer unprinted calculations or model reasoning.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


STEP = re.compile(r"(?m)^\*\*Step (\d+):[^\n]*\*\*")
ASSIGNMENT = re.compile(
    r"(?m)^-\s*(?:Room\s+)?([ABCD]):\s*(\d+)\s*([+-])\s*(\d+)\s*=\s*(\d+)"
)
ROOMS = "ABCD"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(case, response):
    content = response.get("content", "")
    heads = list(STEP.finditer(content))
    faults = []
    parsed_steps = 0
    for j, head in enumerate(heads):
        step = int(head.group(1))
        end = heads[j + 1].start() if j + 1 < len(heads) else len(content)
        found = ASSIGNMENT.findall(content[head.end():end])
        if step != j + 1 or step > case["length"] or len(found) != 2:
            faults.append({"step": step, "kind": "unparseable_step", "assignment_count": len(found)})
            continue
        parsed_steps += 1
        before = case["initial"] if step == 1 else dict(zip(ROOMS, case["trace"][step - 2]))
        after = dict(zip(ROOMS, case["trace"][step - 1]))
        shown_rooms = [room for room, *_ in found]
        expected_rooms = {room for room in ROOMS if before[room] != after[room]}
        if set(shown_rooms) != expected_rooms or len(set(shown_rooms)) != len(shown_rooms):
            faults.append({"step": step, "kind": "assignment_rooms",
                           "shown": shown_rooms, "oracle": sorted(expected_rooms)})
        for room, start, sign, amount, finish in found:
            start, amount, finish = int(start), int(amount), int(finish)
            if start + (amount if sign == "+" else -amount) != finish:
                faults.append({"step": step, "room": room, "kind": "written_arithmetic_identity",
                               "shown": [start, sign, amount, finish]})
            if start != before[room] or finish != after[room]:
                faults.append({"step": step, "room": room, "kind": "oracle_trace_mismatch",
                               "shown": [start, finish], "oracle": [before[room], after[room]]})
    if len(heads) != case["length"]:
        faults.append({"kind": "step_count", "shown": len(heads), "expected": case["length"]})
    return {"id": case["id"], "length": case["length"], "finish_reason": response.get("finish_reason"),
            "parsed_steps": parsed_steps, "expected_steps": case["length"],
            "first_fault_step": min((x["step"] for x in faults if "step" in x), default=None),
            "faults": faults}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    records = [json.loads(line) for line in args.run.read_text().splitlines()]
    if records[0]["meta"]["manifest_sha256"] != sha256(args.manifest):
        raise ValueError("run metadata does not identify manifest")
    cases = manifest["cases"]
    if len(records) != len(cases) + 1:
        raise ValueError("run is incomplete")
    if [r["id"] for r in records[1:]] != [c["id"] for c in cases]:
        raise ValueError("case order mismatch")
    audited = [audit(c, r) for c, r in zip(cases, records[1:])]
    output = {"kind": "public_reference_only_displayed_trace_audit",
              "manifest_sha256": sha256(args.manifest), "run_sha256": sha256(args.run),
              "scope": "Visible per-step room assignment lines only; not a model-reasoning audit.",
              "summary": {"cases": len(audited),
                          "fully_parsed": sum(x["parsed_steps"] == x["expected_steps"] for x in audited),
                          "with_oracle_trace_mismatch": sum(any(f["kind"] == "oracle_trace_mismatch" for f in x["faults"]) for x in audited),
                          "with_written_arithmetic_identity_error": sum(any(f["kind"] == "written_arithmetic_identity" for f in x["faults"]) for x in audited)},
              "cases": audited}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}; sha256={sha256(args.output)}")


if __name__ == "__main__":
    main()
