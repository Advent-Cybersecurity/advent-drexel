#!/usr/bin/env python3
"""Compare GGUF tensor descriptors without reading tensor payloads."""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from gguf import GGUFReader


def inventory(path):
    reader = GGUFReader(str(path), mode="r")
    tensors = {}
    for tensor in reader.tensors:
        if tensor.name in tensors:
            raise ValueError(f"duplicate tensor: {tensor.name}")
        tensors[tensor.name] = {
            "type": tensor.tensor_type.name,
            "shape": [int(value) for value in tensor.shape],
            "payload_bytes": int(tensor.n_bytes),
        }
    by_type = defaultdict(lambda: {"count": 0, "payload_bytes": 0})
    for record in tensors.values():
        by_type[record["type"]]["count"] += 1
        by_type[record["type"]]["payload_bytes"] += record["payload_bytes"]
    return {
        "file_bytes": path.stat().st_size,
        "tensor_count": len(tensors),
        "payload_bytes": sum(record["payload_bytes"] for record in tensors.values()),
        "by_type": dict(sorted(by_type.items())),
    }, tensors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    reference, ref_tensors = inventory(args.reference)
    candidate, can_tensors = inventory(args.candidate)
    if set(ref_tensors) != set(can_tensors):
        raise ValueError("tensor name sets differ")
    changes = []
    for name in sorted(ref_tensors):
        old, new = ref_tensors[name], can_tensors[name]
        if old != new:
            changes.append({"name": name, "reference": old, "candidate": new})
    result = {
        "schema": "gguf-tensor-topology-comparison-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "GGUFReader descriptors only; no tensor payload comparison",
        "reference": reference,
        "candidate": candidate,
        "file_byte_difference_candidate_minus_reference": candidate["file_bytes"] - reference["file_bytes"],
        "payload_byte_difference_candidate_minus_reference": candidate["payload_bytes"] - reference["payload_bytes"],
        "changed_descriptor_count": len(changes),
        "changed_descriptors": changes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "file_byte_difference_candidate_minus_reference",
        "payload_byte_difference_candidate_minus_reference",
        "changed_descriptor_count",
    )}, indent=2))


if __name__ == "__main__":
    main()
