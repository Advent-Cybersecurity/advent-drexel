#!/usr/bin/env python3
"""Replay two exposed V4 development cases on fresh reference-only servers."""

import hashlib
import json
import subprocess
import time
from pathlib import Path

import calibrate_reference_structural_quality_v3 as v3


ROOT = Path(__file__).resolve().parent.parent
SERVER = Path("/tmp/drexel-inference-study/llama-b12283/llama-server")
MODEL = Path("/home/kali/Desktop/MalDev/.research-cache/qwen3-4b-instruct-2507-bartowski-q4_k_m.gguf")
MANIFEST = ROOT / "data/frontier-quality-reference-structural-dev-v4-2026-11-13.json"
BASELINE = ROOT / "data/frontier-quality-reference-structural-dev-v4-run-2026-11-13.jsonl"
OUTPUT = ROOT / "data/frontier-quality-reference-v4-restart-stability-2026-11-13.json"
IDS = ("state-01", "state-06")
SERVER_SHA256 = "64da0db0262aa9a201b27eccc8fdac336bc42ae990c652d31125c6967665187c"
MANIFEST_SHA256 = "c565270b75737774d20becd3db623400d747ea3082a74f43850900c4fcff9676"
BASELINE_SHA256 = "39f8f80ce74184027a8ac5ec4c787a4e7bcf7f1ad452c4ca24a48f4918a05f8a"
BASE = "http://127.0.0.1:8101"


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return digest_bytes(path.read_bytes())


def response_record(choice, response, case):
    content = choice["message"].get("content", "")
    return {
        "id": case["id"], "gold": case["gold"], "content": content,
        "content_sha256": digest_bytes(content.encode()),
        "finish_reason": choice.get("finish_reason"),
        "usage": response.get("usage"), "timings": response.get("timings"),
    }


def run_server(block, cases):
    command = [str(SERVER), "-m", str(MODEL), "-ngl", "0", "-t", "4", "-tb", "4",
               "-c", "4096", "-b", "512", "-ub", "512", "-np", "1", "-lm", "mmap",
               "--no-repack", "--offline", "--no-ui", "--host", "127.0.0.1", "--port", "8101"]
    log_path = ROOT / f"data/frontier-quality-reference-v4-restart-server-{block}-2026-11-13.log"
    started = time.monotonic()
    with log_path.open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(180):
                if process.poll() is not None:
                    raise RuntimeError(f"server exited early with {process.returncode}")
                try:
                    if v3.request_json(BASE + "/health", timeout=2).get("status") == "ok":
                        break
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise TimeoutError("server did not become healthy")
            ids = {m.get("id") for m in v3.request_json(BASE + "/v1/models")["data"]}
            if ids.isdisjoint({str(MODEL), str(MODEL.resolve())}):
                raise ValueError("server reports a different model path")
            outputs = []
            for case in cases:
                payload = {
                    "messages": [{"role": "system", "content": v3.PROMPT},
                                 {"role": "user", "content": case["question"]}],
                    "temperature": 0, "max_tokens": v3.MAX_TOKENS, "stream": False,
                }
                response = v3.request_json(BASE + "/v1/chat/completions", payload, timeout=240)
                outputs.append(response_record(response["choices"][0], response, case))
            return {"block": block, "command": command, "block_wall_seconds": time.monotonic() - started,
                    "log_path": str(log_path.relative_to(ROOT)), "responses": outputs}
        finally:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=20)


def main():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    for path, expected in ((SERVER, SERVER_SHA256), (MODEL, v3.REFERENCE_SHA256),
                           (MANIFEST, MANIFEST_SHA256), (BASELINE, BASELINE_SHA256)):
        if digest(path) != expected:
            raise ValueError(f"hash mismatch: {path}")
    manifest = json.loads(MANIFEST.read_text())
    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    cases = [cases_by_id[case_id] for case_id in IDS]
    baseline_rows = [json.loads(line) for line in BASELINE.read_text().splitlines()[1:]]
    baseline = {row["id"]: row for row in baseline_rows if row["id"] in IDS}
    output = {
        "kind": "public_reference_only_restart_sensitivity",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "notice": "Exposed V4 development cases only; no candidate or sealed holdout was queried.",
        "server_sha256": SERVER_SHA256, "model_sha256": v3.REFERENCE_SHA256,
        "manifest_sha256": MANIFEST_SHA256, "baseline_sha256": BASELINE_SHA256,
        "selected_ids": IDS, "selection": "one previously correct and one previously wrong case",
        "baseline": {case_id: {"content_sha256": digest_bytes(baseline[case_id]["content"].encode()),
                               "finish_reason": baseline[case_id]["finish_reason"],
                               "usage": baseline[case_id]["usage"]} for case_id in IDS},
        "blocks": [],
    }
    for block in (1, 2):
        output["blocks"].append(run_server(block, cases))
    for case_id in IDS:
        hashes = [next(row for row in block["responses"] if row["id"] == case_id)["content_sha256"]
                  for block in output["blocks"]]
        output.setdefault("comparison", {})[case_id] = {
            "replay_texts_identical": hashes[0] == hashes[1],
            "both_replays_match_original": all(h == output["baseline"][case_id]["content_sha256"]
                                                for h in hashes),
        }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(f"{OUTPUT}: sha256={digest(OUTPUT)}")
    print(json.dumps(output["comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
