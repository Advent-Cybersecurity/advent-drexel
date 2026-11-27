#!/usr/bin/env python3
"""Audit tensor-map and unchanged-payload identity between two GGUF files.

Requires the gguf Python package and NumPy. Does not copy model bytes into output.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from gguf import GGUFReader


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    reference = GGUFReader(str(args.reference), mode="r")
    candidate = GGUFReader(str(args.candidate), mode="r")
    ref_tensors = {tensor.name: tensor for tensor in reference.tensors}
    can_tensors = {tensor.name: tensor for tensor in candidate.tensors}
    if len(ref_tensors) != len(reference.tensors) or len(can_tensors) != len(candidate.tensors):
        raise ValueError("Duplicate tensor names")

    unequal_metadata = []
    for name in sorted(set(reference.fields) | set(candidate.fields)):
        ref_field = reference.fields.get(name)
        can_field = candidate.fields.get(name)
        if (
            ref_field is None or can_field is None
            or ref_field.types != can_field.types
            or len(ref_field.parts) != len(can_field.parts)
            or any(not np.array_equal(left, right)
                   for left, right in zip(ref_field.parts, can_field.parts))
        ):
            unequal_metadata.append(name)

    names_match = set(ref_tensors) == set(can_tensors)
    records = []
    for name in sorted(set(ref_tensors) | set(can_tensors)):
        ref = ref_tensors.get(name)
        can = can_tensors.get(name)
        shape_match = ref is not None and can is not None and np.array_equal(ref.shape, can.shape)
        type_match = shape_match and ref.tensor_type == can.tensor_type
        payload_equal = bool(np.array_equal(ref.data, can.data)) if type_match else None
        records.append({
            "name": name,
            "shape_match": bool(shape_match),
            "reference_shape": ref.shape.tolist() if ref is not None else None,
            "candidate_shape": can.shape.tolist() if can is not None else None,
            "reference_type": ref.tensor_type.name if ref is not None else None,
            "candidate_type": can.tensor_type.name if can is not None else None,
            "reference_payload_bytes": int(ref.n_bytes) if ref is not None else None,
            "candidate_payload_bytes": int(can.n_bytes) if can is not None else None,
            "payload_equal_if_same_type": payload_equal,
        })

    changed = [row["name"] for row in records if row["reference_type"] != row["candidate_type"]]
    unequal_same_type = [row["name"] for row in records if row["payload_equal_if_same_type"] is False]
    result = {
        "schema": "gguf-same-base-audit-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reference": {"file_bytes": args.reference.stat().st_size, "sha256": sha256(args.reference)},
        "candidate": {"file_bytes": args.candidate.stat().st_size, "sha256": sha256(args.candidate)},
        "summary": {
            "metadata_fields_equal": not unequal_metadata,
            "unequal_metadata_fields": unequal_metadata,
            "names_match": names_match,
            "shapes_match": all(row["shape_match"] for row in records),
            "tensor_count": len(records),
            "changed_type_count": len(changed),
            "changed_type_names": changed,
            "unchanged_type_payloads_equal": not unequal_same_type,
            "unequal_same_type_names": unequal_same_type,
            "reference_payload_bytes": sum(row["reference_payload_bytes"] or 0 for row in records),
            "candidate_payload_bytes": sum(row["candidate_payload_bytes"] or 0 for row in records),
        },
        "tensors": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
