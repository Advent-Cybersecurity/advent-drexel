#!/usr/bin/env python3
"""Measure lossless storage compression of local GGUF files.

The script writes temporary compressed and restored files outside the repo.
It verifies byte identity after decompression and removes the test files.
"""

import argparse
import hashlib
import json
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


CODECS = {
    "zstd-3": (lambda src, dst: ["zstd", "-3", "-T1", "-q", "-f", str(src), "-o", str(dst)],
               lambda src: ["zstd", "-d", "-q", "-c", str(src)]),
    "zstd-9": (lambda src, dst: ["zstd", "-9", "-T1", "-q", "-f", str(src), "-o", str(dst)],
               lambda src: ["zstd", "-d", "-q", "-c", str(src)]),
    "gzip-6": (lambda src, dst: ["gzip", "-6", "-n", "-c", str(src)],
               lambda src: ["gzip", "-d", "-c", str(src)]),
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command, output=None):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    with open(output, "wb") if output else open("/dev/null", "wb") as stdout:
        process = subprocess.Popen(command, stdout=stdout, stderr=subprocess.PIPE)
        observed = psutil.Process(process.pid)
        peak_rss = 0
        samples = 0
        while True:
            try:
                peak_rss = max(peak_rss, observed.memory_info().rss)
                samples += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            if process.poll() is not None:
                break
            time.sleep(0.02)
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        exit_code = process.wait()
    wall_seconds = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if exit_code:
        raise RuntimeError(f"{command[0]} exited {exit_code}: {stderr[:500]}")
    return {
        "command": command,
        "wall_seconds": round(wall_seconds, 4),
        "cpu_seconds": round((after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime), 4),
        "sampled_peak_rss_bytes": peak_rss,
        "rss_samples": samples,
        "exit_code": exit_code,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+", type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": sys.version.split()[0],
            "zstd": subprocess.check_output(["zstd", "--version"], text=True).strip(),
            "gzip": subprocess.check_output(["gzip", "--version"], text=True).splitlines()[0],
        },
        "host": {"platform": platform.platform(), "logical_cpu_count": psutil.cpu_count(),
                 "memory_bytes": psutil.virtual_memory().total},
        "notes": "Source files were in /tmp tmpfs. Output and restore files were in --work-dir. CPU and wall times include file I/O. Peak RSS was sampled every ~20 ms and may miss short peaks.",
        "models": [],
    }
    for model in args.models:
        if not model.is_file():
            raise FileNotFoundError(model)
        original_size = model.stat().st_size
        original_hash = sha256(model)
        item = {"model": model.name, "source_path": str(model), "original_bytes": original_size,
                "original_sha256": original_hash, "codecs": []}
        print(f"Testing {model.name} ({original_size} bytes)", flush=True)
        for codec, (compress, decompress) in CODECS.items():
            suffix = ".gz" if codec.startswith("gzip") else ".zst"
            packed = args.work_dir / f"{model.stem}.{codec}{suffix}"
            restored = args.work_dir / f"{model.stem}.{codec}.restored.gguf"
            try:
                compression = run(compress(model, packed), packed if codec.startswith("gzip") else None)
                packed_size = packed.stat().st_size
                decompression = run(decompress(packed), restored)
                restored_size = restored.stat().st_size
                restored_hash = sha256(restored)
                exact = restored_size == original_size and restored_hash == original_hash
                item["codecs"].append({
                    "codec": codec, "compressed_bytes": packed_size,
                    "saved_bytes": original_size - packed_size,
                    "saved_percent": round(100 * (original_size - packed_size) / original_size, 4),
                    "restored_bytes": restored_size, "restored_sha256": restored_hash,
                    "byte_identical": exact, "compression": compression,
                    "decompression": decompression,
                })
                print(f"  {codec}: {packed_size} bytes, {100 * (original_size - packed_size) / original_size:.2f}% saved, exact={exact}", flush=True)
                if not exact:
                    raise RuntimeError(f"Restored file differs from source: {codec} {model.name}")
            finally:
                packed.unlink(missing_ok=True)
                restored.unlink(missing_ok=True)
        results["models"].append(item)
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
