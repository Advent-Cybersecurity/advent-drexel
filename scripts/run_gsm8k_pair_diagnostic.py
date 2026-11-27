#!/usr/bin/env python3
"""Run a pinned, public GSM8K diagnostic on one local llama.cpp server.

The manifest is frozen before model calls. Run each model in a separate server
process with identical flags, then score the paired raw responses offline.
"""

import argparse
import hashlib
import json
import math
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


SOURCE_SHA256 = "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
SEED = 20261112
DEV_N = 12
EVAL_N = 200
SYSTEM = (
    "Solve the math problem. Show concise work. End the final line with "
    "#### followed by only the numeric answer."
)
MAX_TOKENS = 256
BOOTSTRAP_SEED = 212022
BOOTSTRAP_DRAWS = 20000
ONE_SIDED_ALPHA = 0.05
NONINFERIORITY_MARGIN = 0.05
ABSOLUTE_FLOOR = 0.60
FINAL_RE = re.compile(r"(?:^|\n)####\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*$")
GOLD_RE = re.compile(r"####\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_rows(path):
    actual = sha256(path)
    if actual != SOURCE_SHA256:
        raise ValueError(f"test split SHA-256 mismatch: {actual}")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if len(rows) != 1319:
        raise ValueError(f"expected 1319 rows, got {len(rows)}")
    return rows


def make_manifest(source, output):
    rows = source_rows(source)
    indices = list(range(len(rows)))
    random.Random(SEED).shuffle(indices)
    selected = indices[: DEV_N + EVAL_N]
    manifest = {
        "source_url": "https://github.com/openai/grade-school-math/blob/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/data/test.jsonl",
        "source_sha256": SOURCE_SHA256,
        "sampling_seed": SEED,
        "dev_count": DEV_N,
        "eval_count": EVAL_N,
        "system_prompt": SYSTEM,
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "sample": [
            {"split": "dev" if pos < DEV_N else "eval", "row": index,
             "question_sha256": hashlib.sha256(rows[index]["question"].encode()).hexdigest()}
            for pos, index in enumerate(selected)
        ],
    }
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {output}; sha256={sha256(output)}")


def request_json(url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_model(source, manifest_path, output, url, model_label, model_sha256):
    rows = source_rows(source)
    manifest = json.loads(manifest_path.read_text())
    if manifest["source_sha256"] != SOURCE_SHA256:
        raise ValueError("manifest source mismatch")
    for _ in range(60):
        try:
            health = request_json(url + "/health", timeout=2)
            if health.get("status") == "ok":
                break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("server did not become healthy")
    if output.exists():
        raise FileExistsError(f"refusing to replace {output}")
    meta = {
        "manifest_sha256": sha256(manifest_path),
        "model_label": model_label,
        "model_sha256": model_sha256,
        "server_url": url,
        "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with output.open("w") as stream:
        stream.write(json.dumps({"meta": meta}) + "\n")
        for count, case in enumerate(manifest["sample"], 1):
            row = rows[case["row"]]
            if hashlib.sha256(row["question"].encode()).hexdigest() != case["question_sha256"]:
                raise ValueError(f"question mismatch at row {case['row']}")
            payload = {
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": row["question"]}],
                "temperature": 0,
                "max_tokens": MAX_TOKENS,
                "stream": False,
            }
            started = time.monotonic()
            try:
                response = request_json(url + "/v1/chat/completions", payload, timeout=120)
                choice = response["choices"][0]
                record = {
                    "row": case["row"], "split": case["split"],
                    "content": choice["message"].get("content", ""),
                    "finish_reason": choice.get("finish_reason"),
                    "usage": response.get("usage"), "timings": response.get("timings"),
                    "wall_seconds": time.monotonic() - started,
                }
            except Exception as exc:
                record = {
                    "row": case["row"], "split": case["split"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "wall_seconds": time.monotonic() - started,
                }
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            if count % 20 == 0:
                print(f"{model_label}: {count}/{len(manifest['sample'])}", flush=True)
    print(f"completed {model_label}: {output}; sha256={sha256(output)}")


def parse_number(pattern, value):
    match = pattern.search(value.strip())
    if not match:
        return None
    from decimal import Decimal
    try:
        return Decimal(match.group(1).replace(",", ""))
    except Exception:
        return None


def load_records(path):
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    if not lines or "meta" not in lines[0]:
        raise ValueError(f"missing metadata in {path}")
    if len({row["row"] for row in lines[1:]}) != len(lines) - 1:
        raise ValueError(f"duplicate row in {path}")
    return lines[0]["meta"], {row["row"]: row for row in lines[1:]}


def exact_binomial_lower(k, n, alpha=ONE_SIDED_ALPHA):
    """One-sided Clopper-Pearson lower limit for a Bernoulli success rate."""
    if k == 0:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        upper_tail = sum(
            math.comb(n, i) * mid**i * (1 - mid)**(n - i)
            for i in range(k, n + 1)
        )
        if upper_tail < alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def paired_bootstrap_lower(subset):
    """Fifth percentile of paired candidate-minus-reference rate resamples."""
    differences = [
        int(x["candidate"]["correct"]) - int(x["reference"]["correct"])
        for x in subset
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    draws = [
        sum(differences[rng.randrange(len(differences))] for _ in differences)
        / len(differences)
        for _ in range(BOOTSTRAP_DRAWS)
    ]
    draws.sort()
    return draws[math.ceil(ONE_SIDED_ALPHA * BOOTSTRAP_DRAWS) - 1]


def conservative_paired_lower(candidate_only, reference_only, n):
    """Bonferroni exact-binomial lower bound for a paired rate difference.

    Each discordance direction is a marginal binomial count. A lower bound on
    candidate-only minus an upper bound on reference-only has at least 95%
    one-sided coverage by the union bound, including zero-discordance cases.
    """
    half_alpha = ONE_SIDED_ALPHA / 2
    candidate_lower = exact_binomial_lower(candidate_only, n, half_alpha)
    reference_upper = 1 - exact_binomial_lower(n - reference_only, n, half_alpha)
    return candidate_lower - reference_upper


def score(source, manifest_path, ref_path, cand_path, output):
    rows = source_rows(source)
    manifest = json.loads(manifest_path.read_text())
    ref_meta, ref = load_records(ref_path)
    cand_meta, cand = load_records(cand_path)
    digest = sha256(manifest_path)
    if ref_meta["manifest_sha256"] != digest or cand_meta["manifest_sha256"] != digest:
        raise ValueError("run manifest hash mismatch")
    cases = []
    for case in manifest["sample"]:
        index = case["row"]
        gold = parse_number(GOLD_RE, rows[index]["answer"])
        if gold is None:
            raise ValueError(f"invalid gold answer at {index}")
        item = {"row": index, "split": case["split"], "gold": str(gold)}
        for label, records in [("reference", ref), ("candidate", cand)]:
            if index not in records:
                raise ValueError(f"missing {label} row {index}")
            response = records[index]
            guess = parse_number(FINAL_RE, response.get("content", ""))
            item[label] = {
                "answer": None if guess is None else str(guess),
                "correct": guess == gold,
                "invalid": guess is None,
                "error": response.get("error"),
                "finish_reason": response.get("finish_reason"),
                "completion_tokens": (response.get("usage") or {}).get("completion_tokens"),
            }
        cases.append(item)
    summary = {}
    for split in ["dev", "eval"]:
        subset = [x for x in cases if x["split"] == split]
        both = sum(x["reference"]["correct"] and x["candidate"]["correct"] for x in subset)
        ref_only = sum(x["reference"]["correct"] and not x["candidate"]["correct"] for x in subset)
        cand_only = sum(not x["reference"]["correct"] and x["candidate"]["correct"] for x in subset)
        neither = len(subset) - both - ref_only - cand_only
        summary[split] = {
            "n": len(subset), "both_correct": both, "reference_only": ref_only,
            "candidate_only": cand_only, "neither_correct": neither,
            "reference_success": both + ref_only,
            "candidate_success": both + cand_only,
            "candidate_minus_reference_rate": (cand_only - ref_only) / len(subset),
            "reference_invalid": sum(x["reference"]["invalid"] for x in subset),
            "candidate_invalid": sum(x["candidate"]["invalid"] for x in subset),
        }
    evaluation = [x for x in cases if x["split"] == "eval"]
    if len(evaluation) != EVAL_N:
        raise ValueError(f"expected {EVAL_N} evaluation rows")
    paired_lower = paired_bootstrap_lower(evaluation)
    conservative_lower = conservative_paired_lower(
        summary["eval"]["candidate_only"],
        summary["eval"]["reference_only"], EVAL_N,
    )
    reference_lower = exact_binomial_lower(summary["eval"]["reference_success"], EVAL_N)
    candidate_lower = exact_binomial_lower(summary["eval"]["candidate_success"], EVAL_N)
    gates = {
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "one_sided_alpha": ONE_SIDED_ALPHA,
        "candidate_minus_reference_lower": paired_lower,
        "conservative_paired_exact_lower": conservative_lower,
        "noninferiority_margin": NONINFERIORITY_MARGIN,
        "noninferiority_pass": conservative_lower > -NONINFERIORITY_MARGIN,
        "reference_exact_binomial_lower": reference_lower,
        "candidate_exact_binomial_lower": candidate_lower,
        "absolute_floor": ABSOLUTE_FLOOR,
        "absolute_floor_pass": reference_lower > ABSOLUTE_FLOOR and candidate_lower > ABSOLUTE_FLOOR,
    }
    gates["public_diagnostic_pass"] = gates["noninferiority_pass"] and gates["absolute_floor_pass"]
    result = {"manifest_sha256": digest, "reference_raw_sha256": sha256(ref_path),
              "candidate_raw_sha256": sha256(cand_path), "reference": ref_meta,
              "candidate": cand_meta, "summary": summary, "gates": gates, "cases": cases}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"summary": summary, "gates": gates}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--manifest", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--url", required=True)
    run.add_argument("--model-label", required=True)
    run.add_argument("--model-sha256", required=True)
    evaluate = sub.add_parser("score")
    for name in ["source", "manifest", "reference", "candidate", "output"]:
        evaluate.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        make_manifest(args.source, args.manifest)
    elif args.command == "run":
        run_model(args.source, args.manifest, args.output, args.url,
                  args.model_label, args.model_sha256)
    else:
        score(args.source, args.manifest, args.reference, args.candidate, args.output)


if __name__ == "__main__":
    main()
