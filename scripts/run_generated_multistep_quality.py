#!/usr/bin/env python3
"""Freeze and score a paired, generated benign multistep quality pilot.

Development questions and responses precede the evaluation freeze. The runner
sends questions only. Evaluation questions, prompt, model hashes, parser and
decision rule are fixed in the evaluation manifest before either model runs.
"""

import argparse
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path


VERSION = 4
PROMPTS = {
    "reasoned_512": "Solve the problem step by step. Show the intermediate quantities and check the arithmetic. Finish with one separate line: The final answer is N. Replace N with the integer answer. Do not write anything after that line.",
}
FAMILIES = ("arithmetic", "state")
NUMBER = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
ANY_NUMBER = re.compile(rf"(?<![\w.,])({NUMBER})(?![\w,])")
FINAL_LINE = re.compile(rf"(?:^|\n)\s*The final answer is\s+({NUMBER})\.?\s*$", re.I)
NUMERIC_ONLY = re.compile(r"[-+]?\d+")
JOINT_ALPHA = 0.05
BOUND_ALPHA = JOINT_ALPHA / 6  # Two families times three asserted bounds.
FLOOR = 0.60
MARGIN = 0.05
MAX_TOKENS = 512


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write_new(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {path}; sha256={digest(path)}", flush=True)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def make_arithmetic(rng, serial):
    template = rng.randrange(4)
    a, b, c, d = rng.randint(3, 12), rng.randint(4, 15), rng.randint(2, 9), rng.randint(3, 11)
    x = rng.randint(2, min(20, a * b - 1))
    ordered = None
    if template == 0:
        question = (f"A museum has {a} boxes of cards with {b} cards in each box. "
                    f"It receives {c} bundles with {d} cards in each bundle, then gives away {x} cards. "
                    "How many cards does it have now?")
        gold = a * b + c * d - x
    elif template == 1:
        question = (f"A school buys {a} packs of {b} pencils each. It uses {x} pencils, "
                    f"then buys {c} more packs of {d} pencils each. "
                    "How many unused pencils does it have?")
        gold = a * b - x + c * d
    elif template == 2:
        question = (f"A bakery makes {a} trays with {b} rolls on each tray. "
                    f"It makes another {c} trays with {d} rolls on each. "
                    f"It sells {x} rolls before closing. How many rolls remain?")
        gold = a * b + c * d - x
    else:
        ordered = rng.randint(1, min(10, a * b - 1))
        question = (f"A workshop makes {b} parts per hour for {a} hours. "
                    f"It marks {ordered} as defective and completes {c} orders of {d} parts each. "
                    "How many usable parts are left after the orders?")
        gold = a * b - ordered - c * d
        # Ensure positive outputs while keeping the same operation structure.
        if gold <= 0:
            ordered = 1
            c = 2
            d = 3
            gold = a * b - ordered - c * d
            question = (f"A workshop makes {b} parts per hour for {a} hours. "
                        f"It marks {ordered} as defective and completes {c} orders of {d} parts each. "
                        "How many usable parts are left after the orders?")
    return {"id": f"arithmetic-{serial:04d}", "family": "arithmetic",
            "question": question, "gold": gold,
            "trace": {"template": template, "a": a, "b": b, "c": c,
                      "d": d, "x": x, "defective_parts": ordered}}


def make_state(rng, serial):
    names = rng.sample(("Oak", "Pine", "Maple", "Cedar", "Birch"), 3)
    template = rng.randrange(4)
    target, second, third = template % 3, (template + 1) % 3, (template + 2) % 3
    fraction = 2 if template < 2 else 3
    x, y, z = [rng.randint(2, 8) for _ in range(3)]
    q, r = rng.randint(9, 18), rng.randint(12, 23)
    counts = [0, 0, 0]
    counts[target] = rng.randint(42, 72)
    counts[second] = 2 * q - x
    counts[third] = fraction * r - q
    state = counts.copy()
    state[target] -= x; state[second] += x
    if state[second] % 2:
        raise AssertionError("second room was not divisible by two")
    half_second = state[second] // 2
    state[second] -= half_second; state[third] += half_second
    if state[third] % fraction:
        raise AssertionError("third room was not evenly divisible")
    share_third = state[third] // fraction
    state[third] -= share_third; state[target] += share_third
    state[target] -= y
    state[target] -= z; state[third] += z
    fraction_word = "half" if fraction == 2 else "one third"
    sentences = [
        f"{names[target]} sends {x} books to {names[second]}",
        f"{names[second]} sends half of its then-current books to {names[third]}",
        f"{names[third]} sends {fraction_word} of its then-current books to {names[target]}",
        f"{names[target]} lends out {y} books",
        f"{names[target]} sends {z} books to {names[third]}",
    ]
    question = (f"Three reading rooms start with {counts[0]}, {counts[1]}, and {counts[2]} books "
                f"in {names[0]}, {names[1]}, and {names[2]}, respectively. In order, " +
                "; ".join(sentences) + f". How many books are in {names[target]} at the end?")
    return {"id": f"state-{serial:04d}", "family": "state",
            "question": question, "gold": state[target],
            "trace": {"template": template, "room_names": names,
                      "initial": counts, "target": target, "first_transfer": x,
                      "second_half_transfer": half_second,
                      "third_fraction": fraction, "third_fraction_transfer": share_third,
                      "target_lends": y, "target_final_transfer": z, "final": state}}


def generate_cases(seed, n):
    if n < 1:
        raise ValueError("cases per family must be positive")
    rng = random.Random(seed)
    cases = []
    for family, function in (("arithmetic", make_arithmetic), ("state", make_state)):
        seen = set()
        serial = 0
        while len(seen) < n:
            serial += 1
            case = function(rng, serial)
            qhash = hashlib.sha256(case["question"].encode()).hexdigest()
            if qhash in seen:
                continue
            case["question_sha256"] = qhash
            seen.add(qhash)
            cases.append(case)
    return cases


def validate_manifest(manifest, kind):
    if manifest.get("schema_version") != VERSION or manifest.get("kind") != kind:
        raise ValueError("manifest schema or kind mismatch")
    if kind == "evaluation":
        prompt_id = manifest.get("prompt_id")
        expected_decision = {
            "joint_one_sided_alpha": JOINT_ALPHA,
            "per_asserted_bound_alpha": BOUND_ALPHA,
            "alpha_allocation": "Bonferroni across two families and three asserted bounds each",
            "absolute_floor": FLOOR,
            "noninferiority_margin": MARGIN,
            "paired_bound": "Bonferroni-CP with half of per-assertion alpha per direction",
            "gate_is_per_family": True,
        }
        if (prompt_id not in PROMPTS or manifest.get("system_prompt") != PROMPTS[prompt_id]
                or manifest.get("max_tokens") != MAX_TOKENS or manifest.get("temperature") != 0
                or manifest.get("parser") != "last-numeric-token-on-normal-stop-v1"
                or manifest.get("format_secondary") != "final-answer-is-last-line-v1"
                or manifest.get("decision") != expected_decision):
            raise ValueError("evaluation settings differ from the frozen scorer")
        hashes = manifest.get("model_sha256", {})
        if not isinstance(hashes, dict) or set(hashes) != {"reference", "candidate"} or any(
                not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                for value in hashes.values()):
            raise ValueError("evaluation model hashes are invalid")
    cases = manifest["cases"]
    ids = [case["id"] for case in cases]
    hashes = [case["question_sha256"] for case in cases]
    if len(set(ids)) != len(ids) or len(set(hashes)) != len(hashes):
        raise ValueError("duplicate case ID or question")
    for case in cases:
        if hashlib.sha256(case["question"].encode()).hexdigest() != case["question_sha256"]:
            raise ValueError(f"question hash mismatch: {case['id']}")
        if case["family"] not in FAMILIES or not isinstance(case["gold"], int):
            raise ValueError(f"invalid case: {case['id']}")
    if sum(case["family"] == "arithmetic" for case in cases) != sum(case["family"] == "state" for case in cases):
        raise ValueError("families are unbalanced")
    expected = generate_cases(manifest["generator_seed"], manifest["cases_per_family"])
    if cases != expected:
        raise ValueError("manifest cases or gold differ from deterministic generator")


def prepare_dev(args):
    cases = generate_cases(args.seed, args.per_family)
    manifest = {"schema_version": VERSION, "kind": "development",
                "created_utc": utc_now(), "generator_seed": args.seed,
                "cases_per_family": args.per_family, "generator": "independent-v2",
                "prompt_options": PROMPTS, "max_tokens": MAX_TOKENS,
                "temperature": 0, "cases": cases}
    json_write_new(args.manifest, manifest)


def read_jsonl(path):
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    if not lines or "meta" not in lines[0]:
        raise ValueError(f"missing run metadata: {path}")
    rows = lines[1:]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate response ID: {path}")
    return lines[0]["meta"], {row["id"]: row for row in rows}


def validate_run(manifest_path, run_path, expected_arm=None):
    manifest = json.loads(manifest_path.read_text())
    kind = manifest["kind"]
    validate_manifest(manifest, kind)
    meta, rows = read_jsonl(run_path)
    if meta["manifest_sha256"] != digest(manifest_path):
        raise ValueError(f"manifest digest mismatch: {run_path}")
    if expected_arm and meta["arm"] != expected_arm:
        raise ValueError(f"expected {expected_arm} arm: {run_path}")
    if set(rows) != {case["id"] for case in manifest["cases"]}:
        raise ValueError(f"incomplete or excess responses: {run_path}")
    if kind == "evaluation":
        if meta["model_sha256"] != manifest["model_sha256"][meta["arm"]]:
            raise ValueError(f"model digest mismatch: {run_path}")
        if meta["prompt_id"] != manifest["prompt_id"]:
            raise ValueError(f"prompt mismatch: {run_path}")
    return meta, rows


def freeze_eval(args):
    dev = json.loads(args.dev_manifest.read_text())
    validate_manifest(dev, "development")
    dev_meta, dev_rows = validate_run(args.dev_manifest, args.reference_dev, "reference")
    if args.prompt_id != dev_meta["prompt_id"]:
        raise ValueError("chosen prompt must match reference development run")
    for family in FAMILIES:
        family_cases = [case for case in dev["cases"] if case["family"] == family]
        successes = sum(evaluate_case(case, dev_rows[case["id"]],
                                      "final-answer-is-last-line-v1")["correct"]
                        for case in family_cases)
        if successes / len(family_cases) < FLOOR:
            raise ValueError(f"reference development {family} success below {FLOOR:.0%} floor")
    if args.seed == dev["generator_seed"]:
        raise ValueError("evaluation and development seeds must differ")
    if not re.fullmatch(r"[0-9a-f]{64}", args.candidate_sha256):
        raise ValueError("candidate SHA-256 must be 64 lowercase hex characters")
    cases = generate_cases(args.seed, args.per_family)
    overlap = {case["question_sha256"] for case in dev["cases"]} & {case["question_sha256"] for case in cases}
    if overlap:
        raise ValueError("evaluation questions overlap development questions")
    manifest = {"schema_version": VERSION, "kind": "evaluation",
                "frozen_utc": utc_now(), "generator_seed": args.seed,
                "cases_per_family": args.per_family, "generator": "independent-v2",
                "development_manifest_sha256": digest(args.dev_manifest),
                "reference_development_run_sha256": digest(args.reference_dev),
                "prompt_id": args.prompt_id, "system_prompt": PROMPTS[args.prompt_id],
                "model_sha256": {"reference": dev_meta["model_sha256"],
                                 "candidate": args.candidate_sha256},
                "max_tokens": MAX_TOKENS, "temperature": 0,
                "parser": "last-numeric-token-on-normal-stop-v1",
                "format_secondary": "final-answer-is-last-line-v1",
                "decision": {"joint_one_sided_alpha": JOINT_ALPHA,
                             "per_asserted_bound_alpha": BOUND_ALPHA,
                             "alpha_allocation": "Bonferroni across two families and three asserted bounds each",
                             "absolute_floor": FLOOR,
                             "noninferiority_margin": MARGIN,
                             "paired_bound": "Bonferroni-CP with half of per-assertion alpha per direction",
                             "gate_is_per_family": True},
                "cases": cases}
    json_write_new(args.manifest, manifest)


def request_json(url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run(args):
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest, manifest["kind"])
    model_sha = digest(args.model_file)
    if manifest["kind"] == "evaluation":
        if model_sha != manifest["model_sha256"][args.arm]:
            raise ValueError("model file does not match frozen SHA-256")
        prompt_id = manifest["prompt_id"]
    else:
        if args.arm != "reference":
            raise ValueError("development calibration uses the reference arm only")
        if args.prompt_id is None:
            raise ValueError("development run requires --prompt-id")
        prompt_id = args.prompt_id
    system_prompt = PROMPTS[prompt_id]
    if args.output.exists():
        raise FileExistsError(f"refusing to replace {args.output}")
    base = args.server_url.rstrip("/")
    for _ in range(60):
        try:
            if request_json(base + "/health", timeout=2).get("status") == "ok":
                break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("server did not become healthy")
    server_models = request_json(base + "/v1/models", timeout=10)
    served_ids = {model.get("id") for model in server_models.get("data", [])}
    expected_ids = {str(args.model_file), str(args.model_file.resolve())}
    if served_ids.isdisjoint(expected_ids):
        raise ValueError("server model ID does not match the hashed local model path")
    meta = {"manifest_sha256": digest(args.manifest), "arm": args.arm,
            "model_sha256": model_sha, "model_file": str(args.model_file),
            "server_url": base, "server_models": server_models,
            "prompt_id": prompt_id,
            "run_started_utc": utc_now()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps({"meta": meta}) + "\n")
        for index, case in enumerate(manifest["cases"], 1):
            payload = {"messages": [{"role": "system", "content": system_prompt},
                                    {"role": "user", "content": case["question"]}],
                       "temperature": 0, "max_tokens": manifest["max_tokens"], "stream": False}
            start = time.monotonic()
            try:
                response = request_json(base + "/v1/chat/completions", payload, timeout=180)
                choice = response["choices"][0]
                record = {"id": case["id"], "family": case["family"],
                          "content": choice["message"].get("content", ""),
                          "finish_reason": choice.get("finish_reason"),
                          "usage": response.get("usage"), "timings": response.get("timings"),
                          "wall_seconds": time.monotonic() - start}
            except Exception as exc:
                record = {"id": case["id"], "family": case["family"],
                          "error": f"{type(exc).__name__}: {exc}",
                          "wall_seconds": time.monotonic() - start}
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            if index % 20 == 0:
                print(f"{args.arm}: {index}/{len(manifest['cases'])}", flush=True)
    print(f"completed {args.output}; sha256={digest(args.output)}", flush=True)


def parsed(content, finish_reason, format_rule):
    if finish_reason != "stop":
        return None, False
    text = content.strip()
    hits = list(ANY_NUMBER.finditer(text))
    answer = None
    if hits:
        try:
            answer = Decimal(hits[-1].group(1).replace(",", ""))
        except InvalidOperation:
            pass
    if format_rule == "numeric-only-integer-v1":
        compliant = NUMERIC_ONLY.fullmatch(text) is not None
    elif format_rule == "final-answer-is-last-line-v1":
        compliant = FINAL_LINE.search(text) is not None
    else:
        raise ValueError(f"unknown format rule: {format_rule}")
    return answer, compliant


def evaluate_case(case, record, format_rule):
    answer, compliant = parsed(record.get("content", ""), record.get("finish_reason"), format_rule)
    return {"correct": answer == Decimal(case["gold"]),
            "answer": None if answer is None else str(answer),
            "format_compliant": compliant,
            "normal_stop": record.get("finish_reason") == "stop",
            "error": record.get("error"),
            "completion_tokens": (record.get("usage") or {}).get("completion_tokens")}


def cp_lower(k, n, alpha):
    from scipy.stats import beta
    return 0.0 if k == 0 else float(beta.ppf(alpha, k, n - k + 1))


def cp_upper(k, n, alpha):
    from scipy.stats import beta
    return 1.0 if k == n else float(beta.ppf(1 - alpha, k + 1, n - k))


def dev_summary(args):
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest, "development")
    meta, rows = validate_run(args.manifest, args.reference_run, "reference")
    result = {"manifest_sha256": digest(args.manifest),
              "reference_run_sha256": digest(args.reference_run),
              "prompt_id": meta["prompt_id"], "families": {}}
    format_rule = "final-answer-is-last-line-v1"
    for family in FAMILIES:
        items = [evaluate_case(case, rows[case["id"]], format_rule) for case in manifest["cases"] if case["family"] == family]
        result["families"][family] = {"n": len(items),
                                      "correct": sum(x["correct"] for x in items),
                                      "format_compliant": sum(x["format_compliant"] for x in items),
                                      "normal_stop": sum(x["normal_stop"] for x in items)}
    print(json.dumps(result, indent=2))


def score(args):
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest, "evaluation")
    ref_meta, ref = validate_run(args.manifest, args.reference_run, "reference")
    cand_meta, cand = validate_run(args.manifest, args.candidate_run, "candidate")
    results = {}
    for family in FAMILIES:
        cases = [case for case in manifest["cases"] if case["family"] == family]
        n = len(cases)
        records = [(evaluate_case(case, ref[case["id"]], manifest["format_secondary"]),
                    evaluate_case(case, cand[case["id"]], manifest["format_secondary"])) for case in cases]
        both = sum(a["correct"] and b["correct"] for a, b in records)
        ref_only = sum(a["correct"] and not b["correct"] for a, b in records)
        cand_only = sum(not a["correct"] and b["correct"] for a, b in records)
        neither = n - both - ref_only - cand_only
        ref_success, cand_success = both + ref_only, both + cand_only
        paired_lower = cp_lower(cand_only, n, BOUND_ALPHA / 2) - cp_upper(ref_only, n, BOUND_ALPHA / 2)
        ref_lower = cp_lower(ref_success, n, BOUND_ALPHA)
        cand_lower = cp_lower(cand_success, n, BOUND_ALPHA)
        results[family] = {
            "n": n, "both_correct": both, "reference_only": ref_only,
            "candidate_only": cand_only, "neither_correct": neither,
            "reference_success": ref_success, "candidate_success": cand_success,
            "reference_rate": ref_success / n, "candidate_rate": cand_success / n,
            "candidate_minus_reference_rate": (cand_only - ref_only) / n,
            "conservative_paired_exact_lower": paired_lower,
            "reference_exact_lower": ref_lower, "candidate_exact_lower": cand_lower,
            "absolute_floor_pass": ref_lower > FLOOR and cand_lower > FLOOR,
            "noninferiority_pass": paired_lower > -MARGIN,
            "reference_format_compliant": sum(a["format_compliant"] for a, _ in records),
            "candidate_format_compliant": sum(b["format_compliant"] for _, b in records),
            "reference_normal_stop": sum(a["normal_stop"] for a, _ in records),
            "candidate_normal_stop": sum(b["normal_stop"] for _, b in records),
            "reference_errors": sum(a["error"] is not None for a, _ in records),
            "candidate_errors": sum(b["error"] is not None for _, b in records),
        }
    result = {"manifest_sha256": digest(args.manifest),
              "reference_raw_sha256": digest(args.reference_run),
              "candidate_raw_sha256": digest(args.candidate_run),
              "reference": ref_meta, "candidate": cand_meta,
              "families": results,
              "all_gates_pass": all(x["absolute_floor_pass"] and x["noninferiority_pass"]
                                    for x in results.values()),
              "limits": "Pass applies only to these generated benign families and frozen artifacts; no frontier parity claim."}
    json_write_new(args.output, result)
    print(json.dumps({"families": results, "all_gates_pass": result["all_gates_pass"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    dev = commands.add_parser("prepare-dev")
    dev.add_argument("--manifest", type=Path, required=True)
    dev.add_argument("--seed", type=int, required=True)
    dev.add_argument("--per-family", type=int, default=8)
    dev.set_defaults(func=prepare_dev)
    freeze = commands.add_parser("freeze-eval")
    freeze.add_argument("--dev-manifest", type=Path, required=True)
    freeze.add_argument("--reference-dev", type=Path, required=True)
    freeze.add_argument("--manifest", type=Path, required=True)
    freeze.add_argument("--seed", type=int, required=True)
    freeze.add_argument("--per-family", type=int, default=96)
    freeze.add_argument("--prompt-id", choices=PROMPTS, required=True)
    freeze.add_argument("--candidate-sha256", required=True)
    freeze.set_defaults(func=freeze_eval)
    run_cmd = commands.add_parser("run")
    run_cmd.add_argument("--manifest", type=Path, required=True)
    run_cmd.add_argument("--output", type=Path, required=True)
    run_cmd.add_argument("--server-url", required=True)
    run_cmd.add_argument("--model-file", type=Path, required=True)
    run_cmd.add_argument("--arm", choices=("reference", "candidate"), required=True)
    run_cmd.add_argument("--prompt-id", choices=PROMPTS)
    run_cmd.set_defaults(func=run)
    summary = commands.add_parser("dev-summary")
    summary.add_argument("--manifest", type=Path, required=True)
    summary.add_argument("--reference-run", type=Path, required=True)
    summary.set_defaults(func=dev_summary)
    score_cmd = commands.add_parser("score")
    score_cmd.add_argument("--manifest", type=Path, required=True)
    score_cmd.add_argument("--reference-run", type=Path, required=True)
    score_cmd.add_argument("--candidate-run", type=Path, required=True)
    score_cmd.add_argument("--output", type=Path, required=True)
    score_cmd.set_defaults(func=score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
