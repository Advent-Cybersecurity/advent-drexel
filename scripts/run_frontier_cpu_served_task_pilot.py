#!/usr/bin/env python3
"""Paired benign llama-server CPU accounting for two pinned local GGUF files.

This pilot measures complete request CPU in a warm, fresh server process. It is
not a cold-cache experiment. The server records the selected CPU repack policy.
"""

import argparse
import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


SYSTEM_PROMPT = (
    "Solve the problem step by step. Show the intermediate quantities and check "
    "the arithmetic. Finish with one separate line: The final answer is N. "
    "Replace N with the integer answer. Do not write anything after that line."
)
MODEL_SHA = {
    "reference": "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e",
    "candidate": "952af947c6aabf7b72f7d8e279e76f7bf4b0d12431eb3abb588ef312865622d8",
}
SERVER_SHA = "64da0db0262aa9a201b27eccc8fdac336bc42ae990c652d31125c6967665187c"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_proc_cpu(pid):
    stat = Path(f"/proc/{pid}/stat").read_text()
    fields = stat[stat.rfind(")") + 2:].split()
    ticks = os.sysconf("SC_CLK_TCK")
    return {"user_seconds": int(fields[11]) / ticks,
            "system_seconds": int(fields[12]) / ticks,
            "total_seconds": (int(fields[11]) + int(fields[12])) / ticks}


def read_status(pid):
    out = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith(("VmRSS:", "VmHWM:", "VmSize:", "VmSwap:", "Threads:")):
            key, value = line.split(":", 1)
            out[key] = value.strip()
    return out


def request_json(url, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def file_census(directory):
    files = []
    links = []
    for base, _, names in os.walk(directory):
        for name in names:
            path = Path(base) / name
            rel = str(path.relative_to(directory))
            if path.is_symlink():
                links.append({"path": rel, "target": os.readlink(path)})
            elif path.is_file():
                files.append({"path": rel, "bytes": path.stat().st_size})
    return {"regular_file_count": len(files), "regular_file_bytes": sum(x["bytes"] for x in files),
            "symbolic_link_count": len(links), "regular_files": files, "symbolic_links": links}


def host_controls():
    out = {"platform": platform.platform(), "cpu_model": None,
           "cpu_affinity": sorted(os.sched_getaffinity(0)), "logical_cpu_count": os.cpu_count(),
           "clock_ticks_per_second": os.sysconf("SC_CLK_TCK")}
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            out["cpu_model"] = line.split(":", 1)[1].strip()
            break
    group = Path("/sys/fs/cgroup")
    controls = {}
    for name in ("cpuset.cpus.effective", "cpu.max", "memory.max", "memory.high"):
        path = group / name
        if path.exists():
            controls[name] = path.read_text().strip()
    out["root_cgroup_controls"] = controls
    return out


def run_one(server, model, arm, cases, task_order, port, logdir, repack_policy):
    cmd = [str(server), "-m", str(model), "-ngl", "0", "-t", "4", "-tb", "4",
           "-c", "2048", "-b", "512", "-ub", "512", "-np", "1", "-lm", "mmap",
           "--offline", "--no-ui", "--host", "127.0.0.1", "--port", str(port)]
    if repack_policy == "no-repack":
        cmd.append("--no-repack")
    base = f"http://127.0.0.1:{port}"
    logpath = logdir / f"server-{arm}-{time.time_ns()}.log"
    record = {"arm": arm, "model": str(model), "started_utc": utc(), "argv": cmd,
              "task_order": task_order, "requests": []}
    with logpath.open("wb") as log:
        start = time.monotonic()
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            for _ in range(180):
                if proc.poll() is not None:
                    raise RuntimeError(f"server exited {proc.returncode} before health")
                try:
                    if request_json(base + "/health", timeout=1).get("status") == "ok":
                        break
                except (OSError, urllib.error.URLError, ValueError):
                    pass
                time.sleep(0.5)
            else:
                raise TimeoutError("server health timeout")
            record["ready_wall_seconds"] = time.monotonic() - start
            record["ready_process_cpu"] = read_proc_cpu(proc.pid)
            record["ready_status"] = read_status(proc.pid)
            record["served_models"] = request_json(base + "/v1/models", timeout=10)
            ids = {x.get("id") for x in record["served_models"].get("data", [])}
            if str(model) not in ids and str(model.resolve()) not in ids:
                raise RuntimeError("served model ID differs from pinned model path")
            for case_id in task_order:
                case = cases[case_id]
                payload = {"messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": case["question"]}],
                           "temperature": 0, "max_tokens": 512, "stream": False}
                before = read_proc_cpu(proc.pid)
                before_status = read_status(proc.pid)
                t0 = time.monotonic()
                response = request_json(base + "/v1/chat/completions", payload, timeout=180)
                wall = time.monotonic() - t0
                after = read_proc_cpu(proc.pid)
                after_status = read_status(proc.pid)
                choice = response["choices"][0]
                content = choice["message"].get("content", "")
                record["requests"].append({"id": case_id, "family": case["family"],
                    "question_sha256": sha256_bytes(case["question"].encode()),
                    "system_prompt_sha256": sha256_bytes(SYSTEM_PROMPT.encode()),
                    "gold": case["gold"], "content": content,
                    "content_sha256": sha256_bytes(content.encode()),
                    "finish_reason": choice.get("finish_reason"), "usage": response.get("usage"),
                    "timings": response.get("timings"), "wall_seconds": wall,
                    "cpu_before": before, "cpu_after": after,
                    "cpu_delta_seconds": round(after["total_seconds"] - before["total_seconds"], 6),
                    "status_before": before_status, "status_after": after_status})
            record["after_requests_cpu"] = read_proc_cpu(proc.pid)
            record["after_requests_status"] = read_status(proc.pid)
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
            try:
                pid, status, usage = os.wait4(proc.pid, 0)
            except ChildProcessError:
                pid, status, usage = proc.pid, None, None
            record["wait_status"] = status
            record["whole_server_wall_seconds"] = time.monotonic() - start
            if usage is not None:
                record["whole_server_cpu_seconds"] = usage.ru_utime + usage.ru_stime
                record["whole_server_user_cpu_seconds"] = usage.ru_utime
                record["whole_server_system_cpu_seconds"] = usage.ru_stime
                record["whole_server_peak_rss_bytes"] = usage.ru_maxrss * 1024
                record["whole_server_major_faults"] = usage.ru_majflt
                record["whole_server_minor_faults"] = usage.ru_minflt
            log.flush()
    record["server_log_tail"] = logpath.read_bytes()[-8000:].decode(errors="replace")
    logpath.unlink()
    return record


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=5)
    parser.add_argument("--port", type=int, default=8094)
    parser.add_argument("--repack-policy", choices=("no-repack", "default"), default="no-repack")
    parser.add_argument("--reference-sha", default=MODEL_SHA["reference"])
    parser.add_argument("--candidate-sha", default=MODEL_SHA["candidate"])
    args = parser.parse_args()
    if args.blocks < 1:
        parser.error("blocks must be positive")
    if args.output.exists():
        raise FileExistsError(args.output)
    if sha256(args.server) != SERVER_SHA:
        raise RuntimeError("server SHA-256 differs from pinned binary")
    model_sha = {"reference": args.reference_sha, "candidate": args.candidate_sha}
    for arm in model_sha:
        path = getattr(args, arm)
        if sha256(path) != model_sha[arm]:
            raise RuntimeError(f"{arm} model SHA-256 differs from pinned file")
    manifest = json.loads(args.manifest.read_text())
    cases = {x["id"]: x for x in manifest["cases"]}
    required = ("arithmetic-0001", "state-0001")
    if not all(x in cases for x in required):
        raise RuntimeError("required benign development tasks missing")
    out = {"schema": "frontier-cpu-served-task-pilot-v2", "created_utc": utc(),
           "host": host_controls(), "method": {"blocks": args.blocks,
               "arms": "reference then candidate on odd blocks, reverse on even blocks",
               "task_order": "arithmetic then state on odd blocks, reverse on even blocks",
               "warm_state": "fresh server process per arm; host model file cache not evicted",
               "repack": args.repack_policy, "server_warmup": "default enabled",
               "cpu": "Linux /proc/PID/stat thread-group utime+stime delta surrounding complete HTTP request; wait4 whole server CPU",
               "peak_rss": "wait4 ru_maxrss for whole server lifetime; Linux KiB converted to bytes",
               "excluded": "client Python CPU, OS baseline, and model download",
               "manifest_sha256": sha256(args.manifest)},
           "server": {"path": str(args.server), "sha256": SERVER_SHA},
           "models": {arm: {"path": str(getattr(args, arm)),
                              "bytes": getattr(args, arm).stat().st_size,
                              "sha256": model_sha[arm]} for arm in model_sha},
           "runtime_dir_census": file_census(args.server.parent), "runs": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logdir = args.output.parent
    try:
        for block in range(1, args.blocks + 1):
            arms = ("reference", "candidate") if block % 2 else ("candidate", "reference")
            tasks = required if block % 2 else tuple(reversed(required))
            for arm in arms:
                rec = run_one(args.server, getattr(args, arm), arm, cases, tasks, args.port, logdir, args.repack_policy)
                rec["block"] = block
                out["runs"].append(rec)
                args.output.write_text(json.dumps(out, indent=2) + "\n")
                print(f"block {block} {arm}: CPU {rec['whole_server_cpu_seconds']:.3f} s; "
                      f"RSS {rec['whole_server_peak_rss_bytes']} B", flush=True)
    finally:
        args.output.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {args.output}; sha256={sha256(args.output)}", flush=True)


if __name__ == "__main__":
    main()
