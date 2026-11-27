#!/usr/bin/env python3
"""Measure benign CPU inference and a CPU-only control process.

This script does not download model weights. Pass pinned, locally verified GGUF
files and a llama-bench binary. Each invocation is recorded, including failure.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


BASELINE_CODE = """\
from concurrent.futures import ThreadPoolExecutor
import hashlib
block = b'x' * 1048576
def work(_):
    h = hashlib.sha256()
    for _ in range(512):
        h.update(block)
    return h.hexdigest()
with ThreadPoolExecutor(max_workers=4) as pool:
    print(list(pool.map(work, range(4))))
"""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def measure(command, kind, model_id=None, prompt_tokens=128, generation_tokens=64):
    started = utc_now()
    start_clock = time.monotonic()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        observed = psutil.Process(process.pid)
        peak_rss = 0
        peak_threads = 0
        last_cpu_seconds = 0.0
        last_read_bytes = 0
        samples = 0
        while True:
            try:
                memory = observed.memory_info()
                cpu = observed.cpu_times()
                io = observed.io_counters()
                peak_rss = max(peak_rss, memory.rss)
                peak_threads = max(peak_threads, observed.num_threads())
                last_cpu_seconds = cpu.user + cpu.system
                last_read_bytes = io.read_bytes
                samples += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            if process.poll() is not None:
                break
            time.sleep(0.05)
        exit_code = process.wait()
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
    record = {
        "kind": kind,
        "model_id": model_id,
        "started_utc": started,
        "ended_utc": utc_now(),
        "wall_seconds": round(time.monotonic() - start_clock, 6),
        "exit_code": exit_code,
        "peak_rss_bytes_sampled": peak_rss,
        "peak_threads_sampled": peak_threads,
        "last_sampled_cpu_seconds": round(last_cpu_seconds, 4),
        "last_sampled_disk_read_bytes": last_read_bytes,
        "sample_count": samples,
    }
    if kind == "inference":
        try:
            results = json.loads(out)
            if len(results) != 1 or results[0]["n_prompt"] != prompt_tokens or results[0]["n_gen"] != generation_tokens:
                raise ValueError("unexpected benchmark case count or token settings")
            result = results[0]
            record["benchmark"] = {
                "build_commit": result["build_commit"],
                "backends": result["backends"],
                "model_n_params": result["model_n_params"],
                "n_prompt": result["n_prompt"],
                "n_gen": result["n_gen"],
                "n_threads": result["n_threads"],
                "n_gpu_layers": result["n_gpu_layers"],
                "inference_seconds": result["avg_ns"] / 1e9,
                "tokens_per_second": result["avg_ts"],
            }
        except (ValueError, KeyError, TypeError) as exc:
            record["parse_error"] = str(exc)
            record["stdout_tail"] = out[-1000:]
    else:
        record["baseline_output_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    if exit_code != 0 or "parse_error" in record:
        record["stderr_tail"] = err[-2000:]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llama-bench", type=Path, required=True)
    parser.add_argument("--small-model", type=Path, required=True)
    parser.add_argument("--large-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--prompt-tokens", type=int, default=128)
    parser.add_argument("--generation-tokens", type=int, default=64)
    args = parser.parse_args()
    if min(args.repetitions, args.prompt_tokens, args.generation_tokens) < 1:
        parser.error("repetitions and token counts must be positive")
    models = {"qwen2.5-0.5b-q4_k_m": args.small_model,
              "qwen2.5-1.5b-q4_k_m": args.large_model}
    for path in [args.llama_bench, *models.values()]:
        if not path.is_file():
            parser.error(f"missing file: {path}")
    document = {
        "schema": "benign-inference-resource-study-v1",
        "created_utc": utc_now(),
        "method": {
            "repetitions_per_case": args.repetitions,
            "run_order": "control, 0.5B, 1.5B repeated in cycles",
            "sampling_interval_seconds": 0.05,
            "inference_case": f"synthetic {args.prompt_tokens} prompt tokens plus {args.generation_tokens} generated tokens; one benchmark case per process; no warmup; 4 CPU threads; no GPU layers",
            "control_case": "four Python SHA256 workers, 512 MiB per worker, 2 GiB total input hashed",
            "wall_time_includes": "process startup, model loading, benchmark, shutdown",
            "inference_time_excludes": "process startup and model loading",
        },
        "host": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count_reported": psutil.cpu_count(logical=False),
            "total_memory_bytes": psutil.virtual_memory().total,
            "available_memory_bytes_at_start": psutil.virtual_memory().available,
            "swap_total_bytes": psutil.swap_memory().total,
            "python_version": platform.python_version(),
            "psutil_version": psutil.__version__,
        },
        "runtime": {
            "path": str(args.llama_bench),
            "sha256": sha256(args.llama_bench),
        },
        "models": {name: {"path": str(path), "file_bytes": path.stat().st_size,
                           "sha256": sha256(path)} for name, path in models.items()},
        "runs": [],
    }
    for cycle in range(1, args.repetitions + 1):
        cases = [("control", None, [sys.executable, "-c", BASELINE_CODE])]
        for name, path in models.items():
            cases.append(("inference", name, [str(args.llama_bench), "-m", str(path),
                                              "-p", "0", "-n", "0", "-pg", f"{args.prompt_tokens},{args.generation_tokens}",
                                              "-r", "1", "-t", "4", "-ngl", "0",
                                              "-o", "json", "--no-warmup"]))
        for kind, name, command in cases:
            result = measure(command, kind, name, args.prompt_tokens, args.generation_tokens)
            result["cycle"] = cycle
            document["runs"].append(result)
            print(f"cycle {cycle}: {name or kind}: exit {result['exit_code']}; "
                  f"wall {result['wall_seconds']:.2f}s", flush=True)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
