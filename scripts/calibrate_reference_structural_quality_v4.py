#!/usr/bin/env python3
"""Public reference-only long-chain state calibration. Never query a candidate."""

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import calibrate_reference_structural_quality_v3 as v3
from audit_reference_v3_dependency_depth import longest_path
from audit_reference_v3_query_ancestors import state_ancestors
from audit_reference_v3_relevant_signature_support import canonical


V3_MANIFEST_SHA256 = "7b6db8127f63beb1c0a4779b8232d1d64cfc54cc8c207e69f34d845c94330943"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def topology(case):
    positions, _ = state_ancestors(case)
    events = [case["events"][i - 1] for i in positions]
    return canonical(events, case["target"], False, False)


def every_event_changes_answer(case):
    for i in range(case["length"]):
        reduced = case["events"][:i] + case["events"][i + 1:]
        final, _ = v3.state_replay(case["initial"], reduced)
        if final[case["target"]] == case["gold"]:
            return False
    return True


def build_manifest(seed, v3_manifest_path):
    if digest(v3_manifest_path) != V3_MANIFEST_SHA256:
        raise ValueError("public V3 exclusion manifest hash changed")
    v3_manifest = json.loads(v3_manifest_path.read_text())
    forbidden = {topology(c) for c in v3_manifest["cases"] if c["family"] == "state"}
    rng = random.Random(seed)
    seen = set(forbidden)
    cases, draw_stats = [], {}
    for length, minimum in ((7, 7), (9, 8)):
        rejected = {"insufficient_depth": 0, "irrelevant_event": 0,
                    "numerically_insensitive": 0, "topology_collision": 0}
        draws = 0
        while len([c for c in cases if c["length"] == length]) < 6:
            if draws >= 10000:
                raise RuntimeError(f"low acceptance for {length}-event cell")
            draws += 1
            index = len(cases) + 1
            case = v3.state_case(rng, index, length)
            depth = longest_path(case)
            positions, _ = state_ancestors(case)
            if depth < minimum:
                rejected["insufficient_depth"] += 1
                continue
            if len(positions) != length:
                rejected["irrelevant_event"] += 1
                continue
            if not every_event_changes_answer(case):
                rejected["numerically_insensitive"] += 1
                continue
            signature = topology(case)
            if signature in seen:
                rejected["topology_collision"] += 1
                continue
            seen.add(signature)
            case["dependency_depth"] = depth
            case["relevant_event_count"] = len(positions)
            case["question_sha256"] = hashlib.sha256(case["question"].encode()).hexdigest()
            cases.append(case)
        draw_stats[str(length)] = {"draws": draws, "accepted": 6,
                                   "rejected": rejected}
    assert len(cases) == 12
    assert len({c["question_sha256"] for c in cases}) == 12
    return {"kind": "reference_only_public_development", "schema_version": 4,
            "seed": seed, "source_generator": "V3 state_case grammar",
            "exclusion_manifest_sha256": V3_MANIFEST_SHA256,
            "selection": "Six seven-event cases with depth seven; six nine-event cases with depth at least eight; all listed events symbolically query-relevant and individually numerically sensitive; unique query-relevant operator topology under room renaming; exclude V3 state topologies.",
            "draw_stats": draw_stats,
            "system_prompt": v3.PROMPT, "temperature": 0,
            "max_tokens": v3.MAX_TOKENS,
            "parser": "last-numeric-token-on-normal-stop-v1 with exactly-one-terminal sensitivity",
            "reference_sha256": v3.REFERENCE_SHA256,
            "notice": "Public reference-only development data. Exclude all cases and functional equivalents from sealed tests.",
            "cases": cases}


def run_reference(args):
    manifest = json.loads(args.manifest.read_text())
    expected = build_manifest(manifest["seed"], args.v3_manifest)
    if manifest != json.loads(json.dumps(expected, sort_keys=True)):
        raise ValueError("manifest differs from deterministic generator")
    if digest(args.model_file) != v3.REFERENCE_SHA256:
        raise ValueError("model differs from pinned reference")
    if args.output.exists():
        raise FileExistsError(args.output)
    base = args.server_url.rstrip("/")
    if v3.request_json(base + "/health").get("status") != "ok":
        raise RuntimeError("server not healthy")
    ids = {m.get("id") for m in v3.request_json(base + "/v1/models").get("data", [])}
    if ids.isdisjoint({str(args.model_file), str(args.model_file.resolve())}):
        raise ValueError("server model path differs")
    meta = {"kind": manifest["kind"], "model_sha256": v3.REFERENCE_SHA256,
            "manifest_sha256": digest(args.manifest), "server_url": base,
            "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps({"meta": meta}) + "\n")
        for case in manifest["cases"]:
            payload = {"messages": [{"role": "system", "content": v3.PROMPT},
                                    {"role": "user", "content": case["question"]}],
                       "temperature": 0, "max_tokens": v3.MAX_TOKENS, "stream": False}
            start = time.monotonic()
            try:
                response = v3.request_json(base + "/v1/chat/completions", payload, timeout=240)
                choice = response["choices"][0]
                record = {"id": case["id"], "content": choice["message"].get("content", ""),
                          "finish_reason": choice.get("finish_reason"),
                          "usage": response.get("usage"), "timings": response.get("timings"),
                          "wall_seconds": time.monotonic() - start}
            except Exception as exc:
                record = {"id": case["id"], "error": f"{type(exc).__name__}: {exc}",
                          "wall_seconds": time.monotonic() - start}
            stream.write(json.dumps(record) + "\n")
            stream.flush()
    print(f"completed {args.output}; sha256={digest(args.output)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    own = Path(__file__).parent.parent
    default_v3 = own / "data/frontier-quality-reference-structural-dev-v3-2026-11-13.json"
    gen = sub.add_parser("generate")
    gen.add_argument("--manifest", type=Path, required=True)
    gen.add_argument("--v3-manifest", type=Path, default=default_v3)
    gen.add_argument("--seed", type=int, default=2026111304)
    run = sub.add_parser("run-reference")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--v3-manifest", type=Path, default=default_v3)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--server-url", required=True)
    run.add_argument("--model-file", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        v3.write_new(args.manifest, build_manifest(args.seed, args.v3_manifest))
    elif args.command == "run-reference":
        run_reference(args)
    else:
        v3.score(args)


if __name__ == "__main__":
    main()
