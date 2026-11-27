#!/usr/bin/env python3
"""Record fresh-process CPU resource runs for two benign GGUF artifacts."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_case(command, label, block, prompt_tokens, generation_tokens):
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        start = time.monotonic_ns()
        child = subprocess.Popen(command, stdout=output, stderr=error)
        pid, status, usage = os.wait4(child.pid, 0)
        assert pid == child.pid
        elapsed = (time.monotonic_ns() - start) / 1e9
        output.seek(0)
        error.seek(0)
        stdout = output.read().decode("utf-8", errors="replace")
        stderr = error.read().decode("utf-8", errors="replace")

    result = {
        "block": block,
        "model": label,
        "exit_code": os.waitstatus_to_exitcode(status),
        "wall_seconds": elapsed,
        "user_cpu_seconds": usage.ru_utime,
        "system_cpu_seconds": usage.ru_stime,
        "total_cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_process_rss_bytes": usage.ru_maxrss * 1024,
        "minor_faults": usage.ru_minflt,
        "major_faults": usage.ru_majflt,
        "voluntary_context_switches": usage.ru_nvcsw,
        "involuntary_context_switches": usage.ru_nivcsw,
    }
    if result["exit_code"] == 0:
        try:
            parsed = json.loads(stdout)
            if (len(parsed) != 1 or parsed[0]["n_prompt"] != prompt_tokens
                    or parsed[0]["n_gen"] != generation_tokens):
                raise ValueError("unexpected benchmark case")
            result["benchmark"] = parsed[0]
        except (ValueError, KeyError, TypeError) as exc:
            result["parse_error"] = str(exc)
    if result["exit_code"] or "parse_error" in result:
        result["stdout_tail"] = stdout[-1000:]
        result["stderr_tail"] = stderr[-2000:]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llama-bench", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=5)
    parser.add_argument("--repack", type=int, choices=(0, 1), default=1)
    parser.add_argument("--prompt-tokens", type=int, default=128)
    parser.add_argument("--generation-tokens", type=int, default=64)
    args = parser.parse_args()
    if args.blocks < 1:
        parser.error("blocks must be positive")
    if args.prompt_tokens < 1 or args.generation_tokens < 1:
        parser.error("token counts must be positive")
    for path in [args.llama_bench, args.reference, args.candidate]:
        if not path.is_file():
            parser.error(f"missing file: {path}")

    command_args = [
        "-p", "0", "-n", "0", "-pg", f"{args.prompt_tokens},{args.generation_tokens}", "-r", "1", "-t", "4",
        "-ngl", "0", "-o", "json", "--no-warmup", "--offline",
        "-lm", "mmap", "--poll", "0", "--repack", str(args.repack),
    ]
    document = {
        "schema": "same-base-quantization-pilot-v1",
        "created_utc": stamp(),
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "page_size_bytes": os.sysconf("SC_PAGE_SIZE"),
        },
        "method": {
            "blocks": args.blocks,
            "prompt_tokens": args.prompt_tokens,
            "generation_tokens": args.generation_tokens,
            "order": "reference then candidate on odd blocks; candidate then reference on even blocks",
            "cache_regime": "warm page cache after artifact construction; no cache flushing",
            "command_args": command_args,
            "process_measurement": "Linux wait4 child user/system CPU, maxrss, and faults; wall includes load and shutdown",
            "scope": "synthetic prefill plus generation; no task quality or whole-task cgroup peak",
        },
        "binary": {"sha256": digest(args.llama_bench)},
        "artifacts": {
            "reference": {"file_bytes": args.reference.stat().st_size, "sha256": digest(args.reference)},
            "candidate": {"file_bytes": args.candidate.stat().st_size, "sha256": digest(args.candidate)},
        },
        "runs": [],
    }
    for block in range(1, args.blocks + 1):
        labels = ["reference", "candidate"] if block % 2 else ["candidate", "reference"]
        for label in labels:
            model = args.reference if label == "reference" else args.candidate
            command = [str(args.llama_bench), "-m", str(model), *command_args]
            record = run_case(command, label, block, args.prompt_tokens, args.generation_tokens)
            document["runs"].append(record)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2) + "\n")
            print(f"block {block}: {label}: exit {record['exit_code']}, "
                  f"CPU {record['total_cpu_seconds']:.2f}s, RSS {record['peak_process_rss_bytes'] / 2**20:.1f} MiB", flush=True)
            if record["exit_code"] or "parse_error" in record:
                raise SystemExit("benchmark failed; partial results saved")


if __name__ == "__main__":
    main()
