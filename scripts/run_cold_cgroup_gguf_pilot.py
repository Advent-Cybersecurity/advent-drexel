#!/usr/bin/env python3
"""Exploratory paired cold-cache cgroup pilot for two pinned CPU GGUF files.

Each trial gets an explicit ext4 copy at a new inode and a fresh user systemd
scope. This is a synthetic resource diagnostic, not a task-quality evaluation.
"""

import argparse
import ctypes
import hashlib
import json
import mmap
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


PAGE = os.sysconf("SC_PAGE_SIZE")
OWNERSHIP_MIN_RSS = 256 * 1024 * 1024
OWNERSHIP_MAX_CHARGE_GAP = 16 * 1024 * 1024
SAMPLE_INTERVAL = 0.10


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copy_regular_file(source, destination, expected_hash):
    h = hashlib.sha256()
    total = 0
    with source.open("rb") as src, destination.open("xb") as dst:
        while block := src.read(8 * 1024 * 1024):
            dst.write(block)
            h.update(block)
            total += len(block)
        dst.flush()
        os.fsync(dst.fileno())
    if total != source.stat().st_size or h.hexdigest() != expected_hash:
        raise RuntimeError("copy bytes or source SHA-256 changed")
    if digest(destination) != expected_hash:
        raise RuntimeError("trial-copy SHA-256 failed")
    if not destination.is_file() or destination.stat().st_ino == source.stat().st_ino:
        raise RuntimeError("trial copy did not produce a distinct regular-file inode")
    with destination.open("rb") as handle:
        os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return total


def resident_bytes(path):
    size = path.stat().st_size
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_COPY) as view:
            address = ctypes.addressof(ctypes.c_char.from_buffer(view))
            page_count = (size + PAGE - 1) // PAGE
            vector = (ctypes.c_ubyte * page_count)()
            libc = ctypes.CDLL(None, use_errno=True)
            result = libc.mincore(ctypes.c_void_p(address), ctypes.c_size_t(size), vector)
            if result != 0:
                errno = ctypes.get_errno()
                raise OSError(errno, os.strerror(errno))
            return sum(min(PAGE, size - i * PAGE) for i, value in enumerate(vector) if value & 1)


def read_pairs(path):
    values = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                values[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return values


def read_pressure_totals(path):
    totals = {}
    if not path.is_file():
        return totals
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts:
            for part in parts[1:]:
                if part.startswith("total="):
                    totals[parts[0]] = int(part.split("=", 1)[1])
    return totals


def cgroup_dir():
    lines = Path("/proc/self/cgroup").read_text().splitlines()
    paths = [line.split(":", 2)[2] for line in lines if line.startswith("0::")]
    if len(paths) != 1:
        raise RuntimeError("unified cgroup v2 path unavailable")
    directory = Path("/sys/fs/cgroup") / paths[0].lstrip("/")
    for name in ("memory.current", "memory.peak", "memory.stat", "memory.events"):
        if not (directory / name).is_file():
            raise RuntimeError(f"cgroup {name} unavailable")
    return directory, paths[0]


def control_hierarchy(group):
    """Record inherited controls; ancestor counters are diagnostic, not child-only."""
    controls = {}
    current = group
    root = Path("/sys/fs/cgroup")
    while current != root.parent:
        entry = {}
        for name in ("memory.max", "memory.high", "cpu.max", "cpuset.cpus.effective"):
            path = current / name
            if path.is_file():
                entry[name] = path.read_text().strip()
        path = current / "cpu.stat"
        if path.is_file():
            entry["cpu.stat"] = read_pairs(path)
        controls[str(current)] = entry
        if current == root:
            break
        current = current.parent
    return controls


def active_controls(controls):
    """Compare limits and placement, excluding counters that change by design."""
    return {group: {key: value for key, value in values.items() if key != "cpu.stat"}
            for group, values in controls.items()}


def group_procs(group):
    return sorted(int(pid) for pid in (group / "cgroup.procs").read_text().split())


def swap_current(group):
    path = group / "memory.swap.current"
    return int(path.read_text()) if path.is_file() else None


def process_snapshot(pid, model_path):
    base = Path("/proc") / str(pid)
    status = {}
    try:
        for line in (base / "status").read_text().splitlines():
            if line.startswith(("VmHWM:", "VmRSS:", "RssAnon:", "RssFile:")):
                parts = line.split()
                status[parts[0][:-1] + "_bytes"] = int(parts[1]) * 1024
        model_rss = 0
        in_model_mapping = False
        for line in (base / "smaps").read_text().splitlines():
            parts = line.split()
            if parts and "-" in parts[0] and len(parts) >= 6 and parts[1][0] in "rwx-":
                in_model_mapping = parts[-1] == str(model_path)
            elif in_model_mapping and line.startswith("Rss:"):
                model_rss += int(parts[1]) * 1024
        status["model_mapping_rss_bytes"] = model_rss
        return status
    except (FileNotFoundError, ProcessLookupError):
        return None


def worker(args):
    group, group_path = cgroup_dir()
    worker_prelaunch_resident = resident_bytes(args.model)
    if worker_prelaunch_resident != 0:
        raise RuntimeError(f"model pages became resident before benchmark launch: {worker_prelaunch_resident}")
    initial_current = int((group / "memory.current").read_text())
    initial_peak = int((group / "memory.peak").read_text())
    initial_procs = group_procs(group)
    initial_swap = swap_current(group)
    initial_stat = read_pairs(group / "memory.stat")
    initial_events = read_pairs(group / "memory.events")
    initial_cpu_stat = read_pairs(group / "cpu.stat")
    initial_cpu_pressure = read_pressure_totals(group / "cpu.pressure")
    initial_host_cpu_pressure = read_pressure_totals(Path("/proc/pressure/cpu"))
    initial_controls = control_hierarchy(group)
    if "file_mapped" not in initial_stat or "pgscan" not in initial_stat:
        raise RuntimeError("required cgroup file_mapped or pgscan counter unavailable")
    command = [
        str(args.llama_bench), "-m", str(args.model),
        "-p", "0", "-n", "0", "-pg", f"{args.prompt_tokens},{args.generation_tokens}",
        "-r", "1", "-t", str(args.threads), "-ngl", "0", "-o", "json",
        "--no-warmup", "--offline", "-lm", "mmap", "--poll", "0",
        "--repack", str(args.repack),
    ]
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        start = time.monotonic_ns()
        child = subprocess.Popen(command, stdout=output, stderr=error)
        samples = []
        try:
            child_group = (Path("/proc") / str(child.pid) / "cgroup").read_text().splitlines()
            membership = any(line == f"0::{group_path}" for line in child_group)
            while True:
                pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    child.returncode = os.waitstatus_to_exitcode(status)
                    break
                snapshot = process_snapshot(child.pid, args.model)
                if snapshot is not None:
                    cg_stat = read_pairs(group / "memory.stat")
                    if "file_mapped" not in cg_stat:
                        raise RuntimeError("cgroup file_mapped counter disappeared")
                    snapshot["cgroup_file_mapped_bytes"] = cg_stat["file_mapped"]
                    snapshot["cgroup_file_bytes"] = cg_stat.get("file", 0)
                    snapshot["cgroup_current_bytes"] = int((group / "memory.current").read_text())
                    if args.trace_memory:
                        snapshot["seconds_since_child_launch"] = (time.monotonic_ns() - start) / 1e9
                        snapshot["cgroup_peak_bytes"] = int((group / "memory.peak").read_text())
                        snapshot["cgroup_stat"] = {
                            key: cg_stat.get(key, 0)
                            for key in ("anon", "file", "file_mapped", "kernel", "file_thp",
                                        "anon_thp", "shmem", "active_file", "inactive_file")
                        }
                    samples.append(snapshot)
                time.sleep(SAMPLE_INTERVAL)
        except BaseException:
            if child.poll() is None:
                child.kill()
            child.wait()
            raise
        elapsed = (time.monotonic_ns() - start) / 1e9
        output.seek(0)
        error.seek(0)
        stdout = output.read().decode("utf-8", errors="replace")
        stderr = error.read().decode("utf-8", errors="replace")
    final_stat = read_pairs(group / "memory.stat")
    final_events = read_pairs(group / "memory.events")
    final_cpu_stat = read_pairs(group / "cpu.stat")
    final_cpu_pressure = read_pressure_totals(group / "cpu.pressure")
    final_host_cpu_pressure = read_pressure_totals(Path("/proc/pressure/cpu"))
    final_controls = control_hierarchy(group)
    final_swap = swap_current(group)
    if "file_mapped" not in final_stat or "pgscan" not in final_stat:
        raise RuntimeError("required cgroup file_mapped or pgscan counter disappeared")
    max_model_rss = max((s["model_mapping_rss_bytes"] for s in samples), default=0)
    near_max_samples = [
        s for s in samples
        if s["model_mapping_rss_bytes"] >= OWNERSHIP_MIN_RSS
        and s["model_mapping_rss_bytes"] >= 0.90 * max_model_rss
    ]
    charge_gaps = [s["cgroup_file_mapped_bytes"] - initial_stat["file_mapped"]
                   - s["model_mapping_rss_bytes"] for s in near_max_samples]
    ownership_supported = bool(charge_gaps) and all(
        abs(gap) <= OWNERSHIP_MAX_CHARGE_GAP for gap in charge_gaps)
    event_delta = {key: final_events.get(key, 0) - initial_events.get(key, 0)
                   for key in set(initial_events) | set(final_events)}
    stat_delta = {key: final_stat.get(key, 0) - initial_stat.get(key, 0)
                  for key in set(initial_stat) | set(final_stat)}
    record = {
        "cgroup_path": group_path,
        "initial_cgroup_procs": initial_procs,
        "initial_scope_contains_only_worker": initial_procs == [os.getpid()],
        "child_in_scope_before_load": membership,
        "worker_prelaunch_mincore_resident_bytes": worker_prelaunch_resident,
        "initial_memory_current_bytes": initial_current,
        "initial_memory_peak_bytes": initial_peak,
        "cgroup_memory_peak_bytes": int((group / "memory.peak").read_text()),
        "final_memory_current_bytes": int((group / "memory.current").read_text()),
        "initial_swap_current_bytes": initial_swap,
        "final_swap_current_bytes": final_swap,
        "initial_memory_stat": initial_stat,
        "final_memory_stat": final_stat,
        "memory_stat_delta": stat_delta,
        "memory_events_delta": event_delta,
        "cpu_stat_delta": {key: final_cpu_stat.get(key, 0) - initial_cpu_stat.get(key, 0)
                           for key in set(initial_cpu_stat) | set(final_cpu_stat)},
        "cgroup_cpu_pressure_total_usec_delta": {
            key: final_cpu_pressure.get(key, 0) - initial_cpu_pressure.get(key, 0)
            for key in set(initial_cpu_pressure) | set(final_cpu_pressure)},
        "host_cpu_pressure_total_usec_delta": {
            key: final_host_cpu_pressure.get(key, 0) - initial_host_cpu_pressure.get(key, 0)
            for key in set(initial_host_cpu_pressure) | set(final_host_cpu_pressure)},
        "initial_control_hierarchy": initial_controls,
        "final_control_hierarchy": final_controls,
        "active_controls_unchanged": active_controls(initial_controls) == active_controls(final_controls),
        "sample_count": len(samples),
        "memory_trace_samples": samples if args.trace_memory else None,
        "max_sampled_process_model_mapping_rss_bytes": max(
            (s["model_mapping_rss_bytes"] for s in samples), default=0),
        "max_sampled_cgroup_file_mapped_bytes": max(
            (s["cgroup_file_mapped_bytes"] for s in samples), default=0),
        "near_max_ownership_sample_count": len(near_max_samples),
        "max_near_max_absolute_charge_gap_bytes": max(map(abs, charge_gaps), default=None),
        "ownership_supported_by_simultaneous_sample": ownership_supported,
        "ownership_best_sample": max(near_max_samples, key=lambda s: s["model_mapping_rss_bytes"])
        if near_max_samples else None,
        "exit_code": os.waitstatus_to_exitcode(status),
        "wall_seconds": elapsed,
        "user_cpu_seconds": usage.ru_utime,
        "system_cpu_seconds": usage.ru_stime,
        "total_child_cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_process_rss_bytes": usage.ru_maxrss * 1024,
        "minor_faults": usage.ru_minflt,
        "major_faults": usage.ru_majflt,
    }
    if record["ownership_best_sample"] is not None:
        best = record["ownership_best_sample"]
        record["ownership_best_sample_charge_gap_bytes"] = (
            best["cgroup_file_mapped_bytes"] - initial_stat["file_mapped"]
            - best["model_mapping_rss_bytes"])
    if record["exit_code"] == 0:
        try:
            parsed = json.loads(stdout)
            if len(parsed) != 1 or parsed[0]["n_prompt"] != args.prompt_tokens or parsed[0]["n_gen"] != args.generation_tokens:
                raise ValueError("unexpected benchmark case")
            record["benchmark"] = parsed[0]
        except (ValueError, TypeError, KeyError) as exc:
            record["parse_error"] = str(exc)
    if record["exit_code"] or "parse_error" in record:
        record["stdout_tail"] = stdout[-1000:]
        record["stderr_tail"] = stderr[-2000:]
    print("COLD_RUN_JSON=" + json.dumps(record, separators=(",", ":")), flush=True)
    return 0 if record["exit_code"] == 0 and "parse_error" not in record else 2


def main():
    if "--worker" in sys.argv[1:]:
        parser = argparse.ArgumentParser()
        parser.add_argument("--worker", action="store_true")
        parser.add_argument("--llama-bench", required=True, type=Path)
        parser.add_argument("--model", required=True, type=Path)
        parser.add_argument("--prompt-tokens", required=True, type=int)
        parser.add_argument("--generation-tokens", required=True, type=int)
        parser.add_argument("--threads", required=True, type=int)
        parser.add_argument("--repack", required=True, type=int, choices=(0, 1))
        parser.add_argument("--trace-memory", action="store_true")
        return worker(parser.parse_args())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llama-bench", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--reference-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--copy-dir", required=True, type=Path,
                        help="disposable trial directory on disk-backed ext4")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--blocks", type=int, default=5)
    parser.add_argument("--prompt-tokens", type=int, default=512)
    parser.add_argument("--generation-tokens", type=int, default=128)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repack", type=int, choices=(0, 1), default=0)
    parser.add_argument("--trace-memory", action="store_true",
                        help="retain 100 ms process and cgroup memory snapshots")
    parser.add_argument("--continue-on-reject", action="store_true",
                        help="record all predeclared trials without changing admission checks")
    args = parser.parse_args()
    if min(args.blocks, args.prompt_tokens, args.generation_tokens, args.threads) < 1:
        parser.error("blocks, tokens, and threads must be positive")
    for path in (args.llama_bench, args.reference, args.candidate):
        if not path.is_file():
            parser.error(f"missing file: {path}")
    args.copy_dir.mkdir(parents=True, exist_ok=True)
    fs_type = subprocess.check_output(
        ["findmnt", "--target", str(args.copy_dir.resolve()), "-n", "-o", "FSTYPE"],
        text=True).strip()
    if fs_type != "ext4":
        parser.error(f"cold trial copy directory must be ext4; found {fs_type}")
    for label, path, expected in (
        ("reference", args.reference, args.reference_sha256),
        ("candidate", args.candidate, args.candidate_sha256),
    ):
        if digest(path) != expected.lower():
            parser.error(f"{label} SHA-256 mismatch")
    document = {
        "schema": "cold-cgroup-gguf-pilot-v2",
        "created_utc": utc_now(),
        "host": {"platform": platform.platform(), "machine": platform.machine(),
                 "page_bytes": PAGE, "logical_cpu_count": os.cpu_count(),
                 "allowed_cpu_ids": sorted(os.sched_getaffinity(0)),
                 "cpu_model": next((line.split(":", 1)[1].strip()
                                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                                    if line.startswith("model name")), None)},
        "method": {
            "blocks": args.blocks,
            "order": "reference then candidate on odd blocks; reverse on even blocks",
            "filesystem": fs_type,
            "mincore_max_resident_bytes_before_launch": 0,
            "ownership_min_model_mapping_rss_bytes": OWNERSHIP_MIN_RSS,
            "ownership_max_absolute_charge_gap_bytes": OWNERSHIP_MAX_CHARGE_GAP,
            "ownership_accounting": "simultaneous cgroup file_mapped increase since worker start versus model-mapping RSS",
            "ownership_limit": "file_mapped is cgroup-wide, not inode-specific; charge gap is diagnostic, not a proven error bound",
            "sample_interval_seconds": SAMPLE_INTERVAL,
            "memory_peak": "fresh systemd user scope, read after benchmark child exit",
            "cpu_seconds": "wait4 benchmark child user plus system; excludes Python monitor",
            "wall_seconds": "benchmark child launch through exit, including model load",
            "scope": "synthetic llama-bench only, not task quality",
            "prompt_tokens": args.prompt_tokens,
            "generation_tokens": args.generation_tokens,
            "threads": args.threads,
            "repack": args.repack,
            "trace_memory": args.trace_memory,
            "continue_on_reject": args.continue_on_reject,
        },
        "binary": {"path": str(args.llama_bench.resolve()), "sha256": digest(args.llama_bench)},
        "artifacts": {
            "reference": {"path": str(args.reference.resolve()), "file_bytes": args.reference.stat().st_size,
                          "sha256": args.reference_sha256.lower()},
            "candidate": {"path": str(args.candidate.resolve()), "file_bytes": args.candidate.stat().st_size,
                          "sha256": args.candidate_sha256.lower()},
        },
        "runs": [],
    }
    used_groups = set()
    with tempfile.TemporaryDirectory(prefix="cold-inode-reservations-", dir=args.copy_dir) as retained_dir:
        for block in range(1, args.blocks + 1):
            labels = ("reference", "candidate") if block % 2 else ("candidate", "reference")
            for label in labels:
                source = args.reference if label == "reference" else args.candidate
                expected = args.reference_sha256.lower() if label == "reference" else args.candidate_sha256.lower()
                with tempfile.TemporaryDirectory(prefix=f"cold-{block}-{label}-", dir=args.copy_dir) as trial_dir:
                    trial = Path(trial_dir) / "model.gguf"
                    copy_started_ns = time.monotonic_ns()
                    copy_regular_file(source, trial, expected)
                    copy_seconds = (time.monotonic_ns() - copy_started_ns) / 1e9
                    before = resident_bytes(trial)
                    record = {
                        "block": block, "arm": label, "started_utc": utc_now(),
                        "copy_and_hash_seconds": copy_seconds,
                        "prelaunch_load_average": os.getloadavg(),
                        "trial_device": trial.stat().st_dev, "trial_inode": trial.stat().st_ino,
                        "trial_file_bytes": trial.stat().st_size, "trial_sha256": expected,
                        "prelaunch_mincore_resident_bytes": before,
                        "accepted": False, "rejection_reasons": [],
                    }
                    if before != 0:
                        record["rejection_reasons"].append("prelaunch model pages resident")
                    else:
                        command = [
                            "systemd-run", "--user", "--scope", "--collect",
                            "-p", "MemoryAccounting=yes", sys.executable, str(Path(__file__).resolve()),
                            "--worker", "--llama-bench", str(args.llama_bench.resolve()),
                            "--model", str(trial), "--prompt-tokens", str(args.prompt_tokens),
                            "--generation-tokens", str(args.generation_tokens),
                            "--threads", str(args.threads), "--repack", str(args.repack),
                        ]
                        if args.trace_memory:
                            command.append("--trace-memory")
                        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        lines = [line[len("COLD_RUN_JSON="):] for line in completed.stdout.splitlines()
                                 if line.startswith("COLD_RUN_JSON=")]
                        if len(lines) == 1:
                            record["measurement"] = json.loads(lines[0])
                        else:
                            record["rejection_reasons"].append("worker result absent or duplicated")
                        record["systemd_run_exit_code"] = completed.returncode
                        if completed.returncode:
                            record["rejection_reasons"].append("systemd-run or benchmark failed")
                        if "measurement" in record:
                            m = record["measurement"]
                            if m["cgroup_path"] in used_groups:
                                record["rejection_reasons"].append("scope cgroup path reused")
                            used_groups.add(m["cgroup_path"])
                            if not m["initial_scope_contains_only_worker"]:
                                record["rejection_reasons"].append("unexpected process in scope before benchmark")
                            if not m["child_in_scope_before_load"]:
                                record["rejection_reasons"].append("benchmark child outside scope")
                            if m["initial_memory_peak_bytes"] > m["initial_memory_current_bytes"] + 16 * 1024 * 1024:
                                record["rejection_reasons"].append("scope memory peak predates benchmark")
                            if not m["active_controls_unchanged"]:
                                record["rejection_reasons"].append("cgroup placement or resource controls changed")
                            if m["initial_swap_current_bytes"] is None or m["final_swap_current_bytes"] is None:
                                record["rejection_reasons"].append("swap accounting unavailable")
                            elif m["final_swap_current_bytes"] > m["initial_swap_current_bytes"]:
                                record["rejection_reasons"].append("cgroup swap charge rose during run")
                            if not m["ownership_supported_by_simultaneous_sample"]:
                                record["rejection_reasons"].append("file-page charge ownership unverified")
                            if m["memory_events_delta"].get("oom", 0) or m["memory_events_delta"].get("oom_kill", 0):
                                record["rejection_reasons"].append("cgroup OOM event")
                            if any(m["memory_events_delta"].get(key, 0) > 0
                                   for key in ("high", "max", "oom_group_kill")):
                                record["rejection_reasons"].append("cgroup limit or group OOM event")
                            if "pgscan" not in m["initial_memory_stat"] or "pgscan" not in m["final_memory_stat"]:
                                record["rejection_reasons"].append("cgroup reclaim counter unavailable")
                            if m["memory_stat_delta"].get("pgscan", 0) > 0:
                                record["rejection_reasons"].append("cgroup reclaim during run")
                            if m["exit_code"] or "parse_error" in m:
                                record["rejection_reasons"].append("benchmark output invalid")
                        if completed.stderr:
                            record["systemd_stderr_tail"] = completed.stderr[-1000:]
                    if not record["rejection_reasons"]:
                        try:
                            with trial.open("r+b") as handle:
                                handle.truncate(0)
                            reservation = Path(retained_dir) / f"{block}-{label}.empty"
                            os.link(trial, reservation)
                            record["inode_reserved_after_run"] = True
                        except OSError as exc:
                            record["rejection_reasons"].append(f"inode reservation failed: {exc}")
                    record["accepted"] = not record["rejection_reasons"]
                    record["finished_utc"] = utc_now()
                    record["postrun_load_average"] = os.getloadavg()
                    document["runs"].append(record)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(document, indent=2) + "\n")
                    print(f"block {block} {label}: prelaunch resident {before} B; "
                          f"{'accepted' if record['accepted'] else 'REJECTED ' + ', '.join(record['rejection_reasons'])}",
                          flush=True)
                    if not record["accepted"] and not args.continue_on_reject:
                        raise SystemExit("trial rejected; partial results saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
