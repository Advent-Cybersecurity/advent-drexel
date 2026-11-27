#!/usr/bin/env python3
"""Replay two exposed V4 reference cases with both prompt caches disabled."""

import hashlib
import json
import subprocess
import time
from pathlib import Path

import audit_reference_v4_restart_stability as prior
import calibrate_reference_structural_quality_v3 as v3


ROOT = prior.ROOT
OUTPUT = ROOT / "data/frontier-quality-reference-v4-cache-disabled-2026-11-13.json"
LOG = ROOT / "data/frontier-quality-reference-v4-cache-disabled-server-2026-11-13.log"
BASE = "http://127.0.0.1:8102"


def main():
    if OUTPUT.exists() or LOG.exists():
        raise FileExistsError("cache-disabled output or log already exists")
    for path, expected in ((prior.SERVER, prior.SERVER_SHA256),
                           (prior.MODEL, v3.REFERENCE_SHA256),
                           (prior.MANIFEST, prior.MANIFEST_SHA256),
                           (prior.BASELINE, prior.BASELINE_SHA256)):
        if prior.digest(path) != expected:
            raise ValueError(f"hash mismatch: {path}")
    manifest = json.loads(prior.MANIFEST.read_text())
    cases_by_id = {case["id"]: case for case in manifest["cases"]}
    cases = [cases_by_id[case_id] for case_id in prior.IDS]
    baseline_rows = [json.loads(line) for line in prior.BASELINE.read_text().splitlines()[1:]]
    baseline = {row["id"]: row for row in baseline_rows if row["id"] in prior.IDS}
    command = [str(prior.SERVER), "-m", str(prior.MODEL), "-ngl", "0", "-t", "4", "-tb", "4",
               "-c", "4096", "-b", "512", "-ub", "512", "-np", "1", "-lm", "mmap",
               "--no-repack", "--offline", "--no-ui", "--no-cache-prompt", "--cache-ram", "0",
               "--host", "127.0.0.1", "--port", "8102"]
    started = time.monotonic()
    with LOG.open("x") as log:
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
            if ids.isdisjoint({str(prior.MODEL), str(prior.MODEL.resolve())}):
                raise ValueError("server reports a different model path")
            responses = []
            for case in cases:
                payload = {
                    "messages": [{"role": "system", "content": v3.PROMPT},
                                 {"role": "user", "content": case["question"]}],
                    "temperature": 0, "max_tokens": v3.MAX_TOKENS,
                    "cache_prompt": False, "stream": False,
                }
                result = v3.request_json(BASE + "/v1/chat/completions", payload, timeout=240)
                responses.append(prior.response_record(result["choices"][0], result, case))
        finally:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=20)
    output = {
        "kind": "public_reference_only_cache_disabled_sensitivity",
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "notice": "Exposed V4 development cases only; no candidate or sealed holdout queried.",
        "server_sha256": prior.SERVER_SHA256,
        "model_sha256": v3.REFERENCE_SHA256,
        "manifest_sha256": prior.MANIFEST_SHA256,
        "baseline_sha256": prior.BASELINE_SHA256,
        "selected_ids": prior.IDS,
        "selection": "one previously correct and one previously wrong case",
        "command": command,
        "request_cache_prompt": False,
        "block_wall_seconds": time.monotonic() - started,
        "log_path": str(LOG.relative_to(ROOT)),
        "responses": responses,
        "comparison": {case_id: {
            "same_content_as_original_v4": next(r for r in responses if r["id"] == case_id)["content_sha256"]
                == prior.digest_bytes(baseline[case_id]["content"].encode()),
            "original_content_sha256": prior.digest_bytes(baseline[case_id]["content"].encode()),
        } for case_id in prior.IDS},
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(f"{OUTPUT}: sha256={prior.digest(OUTPUT)}")
    print(json.dumps(output["comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
