#!/usr/bin/env python3
"""Audit public V3 arithmetic cases by deleting one event; no model calls."""

import argparse
import hashlib
import json
from pathlib import Path

from calibrate_reference_structural_quality_v3 import arithmetic_replay


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("kind") != "reference_only_public_development" or manifest.get("schema_version") != 3:
        raise ValueError("requires public V3 development manifest")
    cases = []
    changed = unchanged = invalid = 0
    for case in manifest["cases"]:
        if case["family"] != "arithmetic":
            continue
        checks = []
        for index in range(case["length"]):
            trimmed = case["events"][:index] + case["events"][index + 1:]
            try:
                (active, reserve), _ = arithmetic_replay(case["initial"], trimmed)
                differs = active != case["gold"]
                checks.append({"position": index + 1, "active": active,
                               "reserve": reserve, "changes_answer": differs})
                changed += differs
                unchanged += not differs
            except AssertionError:
                checks.append({"position": index + 1, "invalid_replay": True})
                invalid += 1
        cases.append({"id": case["id"], "length": case["length"],
                      "gold": case["gold"], "checks": checks})
    result = {
        "kind": "public_v3_arithmetic_numeric_sensitivity_audit",
        "manifest_sha256": digest(args.manifest),
        "generator_sha256": digest(Path(__file__).with_name("calibrate_reference_structural_quality_v3.py")),
        "rule": "Delete one event and replay later events from the original initial stock; compare final active stock with frozen gold.",
        "caveat": "A sampled numeric difference is weaker than proving global functional irreducibility or ruling out an alternative shortcut program. Event deletion also changes the generated-task distribution. No model or sealed case was queried.",
        "totals": {"changed": changed, "unchanged": unchanged, "invalid": invalid},
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {args.output}; sha256={digest(args.output)}")


if __name__ == "__main__":
    main()
