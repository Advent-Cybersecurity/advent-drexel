#!/usr/bin/env python3
"""Validate a host-dependent llama-server file set for two benign GGUF loads."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


LOCAL_FILES = (
    "LICENSE",
    "libggml-base.so.0.29.0",
    "libggml-cpu-haswell.so",
    "libggml-rpc.so",
    "libggml.so.0.29.0",
    "libllama-common.so.0.9.0",
    "libllama-server-impl.so",
    "libllama.so.0.9.0",
    "libmtmd.so.0.9.0",
    "llama-server",
)
LOCAL_LINKS = (
    "libggml.so", "libggml-base.so", "libmtmd.so.0", "libllama-common.so",
    "libllama.so", "libggml.so.0", "libllama-common.so.0",
    "libggml-base.so.0", "libmtmd.so", "libllama.so.0",
)
MODEL_SHA = {
    "reference": "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e",
    "candidate": "952af947c6aabf7b72f7d8e279e76f7bf4b0d12431eb3abb588ef312865622d8",
}
SERVER_SHA = "64da0db0262aa9a201b27eccc8fdac336bc42ae990c652d31125c6967665187c"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def cpu_model():
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def get_json(url, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def mapped_regular_files(pid):
    paths = set()
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/"):
            path = Path(fields[5].removesuffix(" (deleted)"))
            if path.is_file():
                paths.add(str(path.resolve()))
    return [{"path": p, "bytes": Path(p).stat().st_size} for p in sorted(paths)]


def run_arm(bundle, arm, port):
    model = bundle / f"{arm}.gguf"
    cmd = [str(bundle / "llama-server"), "-m", str(model), "-ngl", "0", "-t", "4",
           "-tb", "4", "-c", "512", "-b", "512", "-ub", "512", "-np", "1",
           "-lm", "mmap", "--no-repack", "--offline", "--no-ui", "--host",
           "127.0.0.1", "--port", str(port)]
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(bundle)
    with tempfile.TemporaryFile() as log:
        start = time.monotonic()
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, env=env, start_new_session=True)
        record = {"arm": arm, "argv": cmd, "started_utc": utc(),
                  "launch_ld_library_path": env["LD_LIBRARY_PATH"]}
        try:
            for _ in range(180):
                if proc.poll() is not None:
                    raise RuntimeError(f"server exited before health: {proc.returncode}")
                try:
                    if get_json(f"http://127.0.0.1:{port}/health", timeout=1).get("status") == "ok":
                        break
                except (OSError, urllib.error.URLError, ValueError):
                    pass
                time.sleep(0.5)
            else:
                raise TimeoutError("server did not become healthy")
            record["ready_wall_seconds"] = time.monotonic() - start
            models = get_json(f"http://127.0.0.1:{port}/v1/models")
            record["served_model_ids"] = [x.get("id") for x in models.get("data", [])]
            if str(model) not in record["served_model_ids"]:
                raise RuntimeError("unexpected served model")
            response = get_json(f"http://127.0.0.1:{port}/v1/chat/completions", {
                "messages": [{"role": "user", "content": "Reply with the word ready."}],
                "temperature": 0, "max_tokens": 64, "stream": False,
            }, timeout=60)
            record["response_finish_reason"] = response["choices"][0].get("finish_reason")
            record["response_usage"] = response.get("usage")
            record["response_content"] = response["choices"][0]["message"].get("content", "")
            record["response_content_sha256"] = hashlib.sha256(record["response_content"].encode()).hexdigest()
            if record["response_finish_reason"] != "stop" or not record["response_content"].strip():
                raise RuntimeError("chat endpoint did not return a complete nonempty response")
            record["mapped_regular_files"] = mapped_regular_files(proc.pid)
            record["mapped_file_count"] = len(record["mapped_regular_files"])
            mapped_paths = {x["path"] for x in record["mapped_regular_files"]}
            expected_runtime_paths = {str((bundle / name).resolve())
                                      for name in LOCAL_FILES if name != "LICENSE"}
            record["expected_runtime_files_mapped"] = sorted(expected_runtime_paths & mapped_paths)
            record["expected_runtime_files_missing"] = sorted(expected_runtime_paths - mapped_paths)
            record["mapped_host_regular_files"] = [x for x in record["mapped_regular_files"]
                                                    if not x["path"].startswith(str(bundle.resolve()) + os.sep)]
            record["mapped_host_regular_file_bytes"] = sum(x["bytes"] for x in record["mapped_host_regular_files"])
            record["bundle_model_mapped"] = str(model.resolve()) in mapped_paths
            record["bundle_server_mapped"] = str((bundle / "llama-server").resolve()) in mapped_paths
            if not record["bundle_model_mapped"] or record["expected_runtime_files_missing"]:
                raise RuntimeError("model or a required runtime file is absent from the bundle mappings")
        except Exception as exc:
            record["error"] = repr(exc)
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                record["shutdown_error"] = "server did not exit within 20 seconds of SIGTERM"
            log.seek(0)
            record["server_log_tail"] = log.read()[-3000:].decode(errors="replace")
            record["exit_code"] = proc.returncode
        return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime-dir", required=True, type=Path)
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--work-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--port", type=int, default=8095)
    p.add_argument("--reference-sha", default=MODEL_SHA["reference"])
    p.add_argument("--candidate-sha", default=MODEL_SHA["candidate"])
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if digest(args.runtime_dir / "llama-server") != SERVER_SHA:
        raise RuntimeError("server SHA mismatch")
    model_sha = {"reference": args.reference_sha, "candidate": args.candidate_sha}
    for arm in model_sha:
        if digest(getattr(args, arm)) != model_sha[arm]:
            raise RuntimeError(f"{arm} GGUF SHA mismatch")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    document = {"schema": "minimal-host-dependent-bundle-pilot-v1", "created_utc": utc(),
                "platform": platform.platform(), "cpu_model": cpu_model(),
                "allowed_cpu_ids": sorted(os.sched_getaffinity(0)),
                "source_runtime_dir": str(args.runtime_dir.resolve()),
                "scope": "tested CPU-only offline no-repack chat endpoint on this host; host system shared libraries are external",
                "model_materialization": "same-filesystem hardlink to pinned source GGUF for each arm; no second model data copy during test",
                "runtime_materialization": "copy2 of ten named regular files and recreation of ten relative symlinks",
                "model_sha256": model_sha, "runs": []}
    with tempfile.TemporaryDirectory(prefix="frontier-minimal-bundle-", dir=args.work_dir) as temporary:
        bundle = Path(temporary)
        files = []
        for name in LOCAL_FILES:
            source, target = args.runtime_dir / name, bundle / name
            shutil.copy2(source, target)
            files.append({"name": name, "bytes": target.stat().st_size, "sha256": digest(target)})
        for name in LOCAL_LINKS:
            source = args.runtime_dir / name
            os.symlink(os.readlink(source), bundle / name)
        for name in LOCAL_LINKS:
            (bundle / name).resolve(strict=True).relative_to(bundle.resolve())
        document["runtime_files"] = files
        document["runtime_regular_file_bytes"] = sum(x["bytes"] for x in files)
        document["runtime_symbolic_link_count"] = len(LOCAL_LINKS)
        document["models"] = {}
        for arm in model_sha:
            source = getattr(args, arm)
            target = bundle / f"{arm}.gguf"
            os.link(source, target)
            document["models"][arm] = {"bytes": target.stat().st_size,
                                       "sha256": model_sha[arm],
                                       "bundle_regular_file_bytes": document["runtime_regular_file_bytes"] + target.stat().st_size}
        for arm in ("reference", "candidate"):
            rec = run_arm(bundle, arm, args.port)
            rec["mapped_files_from_original_runtime_dir"] = [x["path"] for x in rec.get("mapped_regular_files", [])
                if x["path"].startswith(str(args.runtime_dir.resolve()) + os.sep)]
            document["runs"].append(rec)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2) + "\n")
            if "error" in rec or "shutdown_error" in rec or rec["exit_code"] != 0 or rec["mapped_files_from_original_runtime_dir"]:
                raise RuntimeError(f"{arm} bundle validation failed; inspect {args.output}")
            print(f"{arm}: ready, response, and mapped-file inventory recorded", flush=True)
    print(f"wrote {args.output}; SHA-256 {digest(args.output)}", flush=True)


if __name__ == "__main__":
    main()
