#!/usr/bin/env python3
"""Reproducible, benign same-source CPU and dependent-step quality assay.

Only the reference arm may be used for development. A sealed manifest is created
before either arm sees its evaluation questions. Failed requests count as wrong.
"""

import argparse
import hashlib
import json
import os
import random
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

PROMPT = ("Follow each step in order. Work out the intermediate amounts. "
          "Finish with one line in the form Answer: N, where N is an integer.")
PROMPT_SHA = hashlib.sha256(PROMPT.encode()).hexdigest()
MODEL_SHA = {
    "reference": "b66e0350b994a95e26e9c41f05410c39f1ec84838b96144f494f87a5aaee8bf5",
    "candidate": "eee0176b86f95aff2e794f88c13b613a47c13380131ccdf926de8d650e6402d2",
}
SERVER_SHA = "64da0db0262aa9a201b27eccc8fdac336bc42ae990c652d31125c6967665187c"
ANSWER = re.compile(r"(?:^|\n)\s*Answer:\s*(-?\d+)\s*\.?\s*$", re.I)
NUMBER = re.compile(r"(?<![\w.,])(-?\d+)(?![\w,])")
FLOOR = 0.60
MARGIN = 0.05
ALPHA = 0.05 / 6


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def generate(seed, per_family):
    rng = random.Random(seed)
    cases = []
    for i in range(per_family):
        start, packs, each = rng.randint(28, 84), rng.randint(2, 6), rng.randint(3, 8)
        taken = rng.randint(3, 17)
        variant = rng.randrange(4)
        if variant == 0:
            question = (f"A library has {start} bookmarks. It receives {packs} packs "
                        f"of {each} bookmarks each, then gives away {taken}. "
                        "How many bookmarks remain?")
        elif variant == 1:
            question = (f"A club starts with {start} badges. It makes {packs} trays "
                        f"of {each} badges each and then hands out {taken}. "
                        "How many badges does it have now?")
        elif variant == 2:
            question = (f"A shop has {start} pencils. It adds {packs} boxes "
                        f"with {each} pencils per box and sells {taken}. "
                        "How many pencils are left?")
        else:
            question = (f"A desk begins with {start} tickets. It prints {packs} "
                        f"sheets of {each} tickets each, then discards {taken}. "
                        "How many tickets remain?")
        cases.append({"id": f"arithmetic-{i:04d}", "family": "arithmetic",
                      "question": question, "gold": start + packs * each - taken,
                      "structure": "start+packs*each-taken", "variant": variant})
    for i in range(per_family):
        a = rng.randint(28, 70)
        b = 2 * rng.randint(12, 38)
        moved = 2 * rng.randint(2, 9)
        variant = rng.randrange(4)
        # The second transfer depends on B's balance after the first transfer.
        half = (b + moved) // 2
        gold = a - moved + half
        if variant == 0:
            question = (f"Room A has {a} books and Room B has {b}. First A sends "
                        f"{moved} books to B. Then B sends half of its current books "
                        "to A. How many books are in A now?")
        elif variant == 1:
            question = (f"Box A contains {a} cards and Box B contains {b}. A moves "
                        f"{moved} cards to B; after that, B moves half of what it "
                        "now contains to A. How many cards does A contain?")
        elif variant == 2:
            question = (f"There are {a} tokens at station A and {b} at station B. "
                        f"Move {moved} from A to B. Next, move half of B's new "
                        "total to A. What is A's final token count?")
        else:
            question = (f"Jar A starts with {a} beads and jar B with {b}. Transfer "
                        f"{moved} beads from A to B. Then transfer half of B's "
                        "current beads back to A. How many beads finish in A?")
        cases.append({"id": f"state-{i:04d}", "family": "state",
                      "question": question, "gold": gold,
                      "structure": "A-=m;B+=m;A+=B/2", "variant": variant})
    for case in cases:
        case["question_sha256"] = hashlib.sha256(case["question"].encode()).hexdigest()
    assert len({x["question_sha256"] for x in cases}) == len(cases)
    return cases


def get(url, payload=None, timeout=10):
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def proc_cpu(pid):
    value = Path(f"/proc/{pid}/stat").read_text()
    fields = value[value.rfind(")") + 2:].split()
    return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")


def serve(server, model, cases, arm, port, logpath, output, manifest_sha, block=None):
    cmd = [str(server), "-m", str(model), "-ngl", "0", "-t", "4", "-tb", "4",
           "-c", "1024", "-b", "512", "-ub", "512", "-np", "1", "-lm", "mmap",
           "--offline", "--no-ui", "--no-repack", "--host", "127.0.0.1", "--port", str(port)]
    result = {"arm": arm, "block": block, "argv": cmd, "started_utc": utc(),
              "manifest_sha256": manifest_sha, "model_sha256": sha(model),
              "model_bytes": model.stat().st_size, "requests": []}
    with logpath.open("wb") as log:
        t0 = time.monotonic()
        child = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(120):
                if child.poll() is not None:
                    raise RuntimeError(f"server exited before ready: {child.returncode}")
                try:
                    if get(base + "/health", timeout=1).get("status") == "ok":
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.5)
            else:
                raise TimeoutError("server did not become healthy")
            result["ready_wall_seconds"] = time.monotonic() - t0
            result["ready_cpu_seconds"] = proc_cpu(child.pid)
            served = get(base + "/v1/models")
            ids = {x.get("id") for x in served.get("data", [])}
            if str(model) not in ids and str(model.resolve()) not in ids:
                raise RuntimeError("served model does not match model path")
            for index, case in enumerate(cases, 1):
                before = proc_cpu(child.pid)
                start = time.monotonic()
                row = {"id": case["id"], "family": case["family"]}
                try:
                    response = get(base + "/v1/chat/completions", {
                        "messages": [{"role": "system", "content": PROMPT},
                                     {"role": "user", "content": case["question"]}],
                        "temperature": 0, "max_tokens": 128, "stream": False}, timeout=120)
                    choice = response["choices"][0]
                    row.update({"content": choice["message"].get("content", ""),
                                "finish_reason": choice.get("finish_reason"),
                                "usage": response.get("usage")})
                except Exception as exc:
                    row["error"] = f"{type(exc).__name__}: {exc}"
                row["wall_seconds"] = time.monotonic() - start
                row["cpu_seconds"] = proc_cpu(child.pid) - before
                result["requests"].append(row)
                output.write_text(json.dumps(result, indent=2) + "\n")
                if index % 20 == 0 or index == len(cases):
                    print(f"{arm} {block or ''}: {index}/{len(cases)}", flush=True)
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            pid, status, usage = os.wait4(child.pid, 0)
            assert pid == child.pid
            result.update({"whole_server_cpu_seconds": usage.ru_utime + usage.ru_stime,
                           "whole_server_peak_rss_bytes": usage.ru_maxrss * 1024,
                           "whole_server_wall_seconds": time.monotonic() - t0,
                           "major_faults": usage.ru_majflt,
                           "exit_code": os.waitstatus_to_exitcode(status)})
            output.write_text(json.dumps(result, indent=2) + "\n")
    result["server_log_sha256"] = sha(logpath)
    return result


def score_one(case, row):
    if row.get("error") or row.get("finish_reason") != "stop":
        return False, False
    content = row.get("content", "").strip()
    matches = list(NUMBER.finditer(content))
    answer = int(matches[-1].group(1)) if matches else None
    return answer == case["gold"], bool(ANSWER.search(content))


def cp_lower(k, n, alpha):
    from scipy.stats import beta
    return 0.0 if k == 0 else float(beta.ppf(alpha, k, n - k + 1))


def cp_upper(k, n, alpha):
    from scipy.stats import beta
    return 1.0 if k == n else float(beta.ppf(1 - alpha, k + 1, n - k))


def verify_manifest(manifest):
    if manifest["schema"] != "same-source-chain-assay-v1":
        raise ValueError("manifest schema mismatch")
    if manifest["prompt_sha256"] != PROMPT_SHA or manifest["model_sha256"] != MODEL_SHA:
        raise ValueError("manifest prompt or model mismatch")
    if manifest["cases"] != generate(manifest["seed"], manifest["per_family"]):
        raise ValueError("manifest cases differ from generator")


def prepare(args):
    value = {"schema": "same-source-chain-assay-v1", "kind": args.kind,
             "created_utc": utc(), "seed": args.seed, "per_family": args.per_family,
             "prompt": PROMPT, "prompt_sha256": PROMPT_SHA,
             "model_sha256": MODEL_SHA, "max_tokens": 128, "temperature": 0,
             "server_policy": "b12283, CPU 4 threads, --no-repack, mmap, 1024 context",
             "quality_rule": "last integer after normal stop; errors and truncation wrong",
             "format_secondary": "final Answer: integer line",
             "floor": FLOOR, "margin": MARGIN, "joint_alpha": 0.05,
             "per_bound_alpha": ALPHA, "cases": generate(args.seed, args.per_family)}
    if args.kind == "evaluation":
        if not args.dev_manifest or not args.dev_run:
            raise ValueError("evaluation requires reference development manifest and run")
        dev = json.loads(args.dev_manifest.read_text())
        verify_manifest(dev)
        if dev["kind"] != "development" or dev["seed"] == args.seed:
            raise ValueError("development seed must differ")
        run = json.loads(args.dev_run.read_text())
        if run["arm"] != "reference" or run["manifest_sha256"] != sha(args.dev_manifest):
            raise ValueError("reference development run mismatch")
        rows = {x["id"]: x for x in run["requests"]}
        if len(rows) != len(dev["cases"]):
            raise ValueError("development run incomplete")
        for family in ("arithmetic", "state"):
            items = [x for x in dev["cases"] if x["family"] == family]
            rate = sum(score_one(x, rows[x["id"]])[0] for x in items) / len(items)
            if rate < FLOOR:
                raise ValueError(f"reference development {family} below floor: {rate:.3f}")
        value["development_manifest_sha256"] = sha(args.dev_manifest)
        value["reference_development_run_sha256"] = sha(args.dev_run)
    write_new(args.manifest, value)
    print(f"wrote {args.manifest}; sha256={sha(args.manifest)}")


def run(args):
    manifest = json.loads(args.manifest.read_text())
    verify_manifest(manifest)
    if args.arm == "candidate" and manifest["kind"] != "evaluation":
        raise ValueError("candidate cannot run on development manifest")
    if sha(args.server) != SERVER_SHA or sha(args.model) != MODEL_SHA[args.arm]:
        raise ValueError("server or model SHA-256 mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.blocks:
        if manifest["kind"] != "evaluation":
            raise ValueError("resource blocks require evaluation manifest")
        # A fixed subset, disjoint from dev; blocks repeat identical cases.
        chosen = manifest["cases"][:4] + manifest["cases"][manifest["per_family"]:manifest["per_family"]+4]
        for block in range(1, args.blocks + 1):
            path = args.output.with_name(args.output.stem + f"-block-{block}.json")
            log = path.with_suffix(".log")
            serve(args.server, args.model, chosen, args.arm, args.port, log, path,
                  sha(args.manifest), block)
        return
    order = list(manifest["cases"])
    random.Random(manifest["seed"] + 1103).shuffle(order)
    serve(args.server, args.model, order, args.arm, args.port,
          args.output.with_suffix(".log"), args.output, sha(args.manifest))


def summary(args):
    manifest = json.loads(args.manifest.read_text())
    verify_manifest(manifest)
    ref = json.loads(args.reference.read_text())
    if ref["manifest_sha256"] != sha(args.manifest) or ref["arm"] != "reference":
        raise ValueError("reference run mismatch")
    rr = {x["id"]: x for x in ref["requests"]}
    candidate = None
    if args.candidate:
        candidate = json.loads(args.candidate.read_text())
        if manifest["kind"] != "evaluation" or candidate["manifest_sha256"] != sha(args.manifest):
            raise ValueError("candidate run mismatch")
        cc = {x["id"]: x for x in candidate["requests"]}
    result = {"manifest_sha256": sha(args.manifest), "reference_sha256": sha(args.reference),
              "candidate_sha256": sha(args.candidate) if candidate else None,
              "families": {}, "reference_server_cpu_seconds": ref.get("whole_server_cpu_seconds"),
              "reference_peak_rss_bytes": ref.get("whole_server_peak_rss_bytes")}
    if candidate:
        result.update({"candidate_server_cpu_seconds": candidate.get("whole_server_cpu_seconds"),
                       "candidate_peak_rss_bytes": candidate.get("whole_server_peak_rss_bytes")})
    for family in ("arithmetic", "state"):
        cases = [x for x in manifest["cases"] if x["family"] == family]
        if set(x["id"] for x in cases) - set(rr):
            raise ValueError("incomplete reference run")
        rv = [score_one(x, rr[x["id"]]) for x in cases]
        record = {"n": len(cases), "reference_correct": sum(x[0] for x in rv),
                  "reference_format": sum(x[1] for x in rv),
                  "reference_request_cpu_seconds": sum(rr[x["id"]]["cpu_seconds"] for x in cases)}
        if candidate:
            if set(x["id"] for x in cases) - set(cc):
                raise ValueError("incomplete candidate run")
            cv = [score_one(x, cc[x["id"]]) for x in cases]
            both = sum(a[0] and b[0] for a,b in zip(rv,cv))
            ro = sum(a[0] and not b[0] for a,b in zip(rv,cv))
            co = sum(not a[0] and b[0] for a,b in zip(rv,cv))
            n = len(cases)
            bound = cp_lower(co,n,ALPHA/2)-cp_upper(ro,n,ALPHA/2)
            record.update({"candidate_correct": sum(x[0] for x in cv),
                           "candidate_format": sum(x[1] for x in cv),
                           "both_correct": both, "reference_only": ro,
                           "candidate_only": co, "neither": n-both-ro-co,
                           "paired_difference": (co-ro)/n,
                           "paired_exact_lower": bound,
                           "reference_exact_lower": cp_lower(sum(x[0] for x in rv),n,ALPHA),
                           "candidate_exact_lower": cp_lower(sum(x[0] for x in cv),n,ALPHA),
                           "floor_pass": (cp_lower(sum(x[0] for x in rv),n,ALPHA)>FLOOR and
                                          cp_lower(sum(x[0] for x in cv),n,ALPHA)>FLOOR),
                           "noninferiority_pass": bound > -MARGIN,
                           "candidate_request_cpu_seconds": sum(cc[x["id"]]["cpu_seconds"] for x in cases)})
        result["families"][family] = record
    if candidate:
        result["all_quality_gates_pass"] = all(x["floor_pass"] and x["noninferiority_pass"]
                                                for x in result["families"].values())
    if args.output:
        write_new(args.output, result)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--kind", choices=("development", "evaluation"), required=True)
    prep.add_argument("--manifest", type=Path, required=True)
    prep.add_argument("--seed", type=int, required=True)
    prep.add_argument("--per-family", type=int, required=True)
    prep.add_argument("--dev-manifest", type=Path)
    prep.add_argument("--dev-run", type=Path)
    prep.set_defaults(func=prepare)
    runner = sub.add_parser("run")
    runner.add_argument("--manifest", type=Path, required=True)
    runner.add_argument("--model", type=Path, required=True)
    runner.add_argument("--server", type=Path, required=True)
    runner.add_argument("--arm", choices=("reference", "candidate"), required=True)
    runner.add_argument("--output", type=Path, required=True)
    runner.add_argument("--port", type=int, default=8098)
    runner.add_argument("--blocks", type=int, default=0)
    runner.set_defaults(func=run)
    summ = sub.add_parser("summary")
    summ.add_argument("--manifest", type=Path, required=True)
    summ.add_argument("--reference", type=Path, required=True)
    summ.add_argument("--candidate", type=Path)
    summ.add_argument("--output", type=Path)
    summ.set_defaults(func=summary)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
