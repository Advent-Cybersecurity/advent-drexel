#!/usr/bin/env python3
"""Reference-only public development calibration, clarified wording version 2.

This script has no candidate mode and cannot make a sealed evaluation ledger.
Its six arithmetic and six state patterns are development material. Conditional
branches yield separate executed structures. Exclude their canonical structures
and functional equivalents from any later sealed holdout.
"""

import argparse
import hashlib
import json
import random
import re
import time
import urllib.request
from decimal import Decimal
from pathlib import Path


REFERENCE_SHA256 = "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"
PROMPT = ("Use brief calculations with only the intermediate quantities needed to solve the problem. "
          "Finish with exactly one separate line: The final answer is N. "
          "Replace N with the integer answer. Write nothing after that line.")
MAX_TOKENS = 768
NUMBER = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
ANY_NUMBER = re.compile(rf"(?<![\w.,])({NUMBER})(?![\w,])")
FINAL_LINE = re.compile(rf"(?:^|\n)\s*The final answer is\s+({NUMBER})\.?\s*$", re.I)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(obj, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(f"wrote {path}; sha256={digest(path)}", flush=True)


def arithmetic_case(rng, pattern, variant):
    a, b, c, d = rng.randint(4, 10), rng.randint(6, 12), rng.randint(3, 8), rng.randint(5, 11)
    x, y, k = rng.randint(3, 11), rng.randint(2, 7), rng.randint(2, 4)
    first, second = a * b, c * d
    if pattern == 1:
        left = first - x
        bonus = left // k
        gold = left + bonus
        question = (f"A print shop starts with {a} cartons of {b} cards each. It uses {x} cards. "
                    f"It then pools the remaining cards and prints one extra card for each complete group of {k}. "
                    "Cards in an incomplete group remain on hand but produce no extra card. "
                    "How many cards are on hand now?")
        trace = [first, left, bonus, gold]
        independent = first - x + (first - x) // k
    elif pattern == 2:
        damaged = second // k
        gold = first + second - damaged - x
        question = (f"A school receives {a} packs of {b} pencils and then {c} packs of {d} pencils. "
                    f"Pool all pencils in the second delivery, ignoring pack boundaries. "
                    f"One pencil from each complete group of {k} in that pool is damaged. "
                    f"The school then gives out {x} good pencils. How many good pencils remain?")
        trace = [first, second, damaged, gold]
        independent = first + (second - second // k) - x
    elif pattern == 3:
        left = first - x
        reserved = left // k
        gold = left - reserved + second
        question = (f"A bakery makes {a} trays of {b} rolls each. It sells {x} rolls, "
                    f"then pools all remaining rolls, ignoring tray boundaries, and reserves one roll "
                    f"from each complete group of {k} in that pool. "
                    f"It later makes {c} more trays of {d} rolls each. "
                    "How many rolls are available for sale, excluding those reserved?")
        trace = [first, left, reserved, second, gold]
        independent = first - x - ((first - x) // k) + second
    elif pattern == 4:
        threshold = first + x + (-3 if variant == 1 else 3)
        restock = second if first + x >= threshold else y
        gold = first + x + restock - y
        question = (f"A museum has {a} boxes of {b} cards each and receives {x} returned cards. "
                    f"If it then has at least {threshold} cards, it orders {c} bundles of {d} cards each; "
                    f"otherwise it orders exactly {y} cards. After the order arrives, it gives away {y} cards. "
                    "How many cards remain?")
        trace = [first, first + x, threshold, restock, gold]
        independent = first + x - y + (second if first + x >= threshold else y)
    elif pattern == 5:
        reserve = first // k
        returned = reserve // 2
        gold = first - reserve - x + returned
        question = (f"A warehouse has {a} crates of {b} labels each. It pools all labels, "
                    f"ignoring crate boundaries, and moves one label from each complete group of {k} "
                    f"in that pool into reserve. It uses {x} labels "
                    "from the active stock, then returns half of the reserve to active stock, "
                    "rounding down. How many labels are in active stock now?")
        trace = [first, reserve, first - reserve, returned, gold]
        independent = first - x - (first // k) + ((first // k) // 2)
    else:
        usable = first - x + second - y
        reserved = usable // k
        gold = usable - reserved
        question = (f"A workshop has {a} bins of {b} parts each and {c} bins of {d} parts each. "
                    f"It removes {x} defective parts from the first set and {y} from the second. "
                    f"It pools all usable parts, ignoring bin boundaries, then sets aside one part "
                    f"from every complete group of {k} in that pool. "
                    "How many usable parts are not set aside?")
        trace = [first, second, first - x, second - y, usable, reserved, gold]
        independent = (first + second - x - y) - ((first + second - x - y) // k)
    assert gold == independent and gold >= 0
    branch = f"-{'high' if variant == 1 else 'low'}" if pattern == 4 else ""
    return {"id": f"arithmetic-{pattern:02d}-{variant:02d}", "family": "arithmetic",
            "structure_id": f"development-arithmetic-{pattern:02d}{branch}", "question": question,
            "gold": gold, "trace": trace,
            "parameters": {"a": a, "b": b, "c": c, "d": d, "x": x, "y": y, "k": k}}


STATE_PATTERNS = (
    (("A", "B", "x"), ("B", "C", "half"), ("C", "D", "half"), ("D", "A", "third"), "A"),
    (("A", "C", "third"), ("C", "B", "half"), ("B", "D", "quarter"), ("B", "A", "half"), ("D", "A", "quarter"), "A"),
    (("A", "B", "x"), ("C", "B", "y"), ("B", "D", "quarter"), ("D", "C", "half"), "C"),
    (("D", "A", "x"), ("A", "B", "half"), ("B", "C", "half"), ("C", "D", "third"), ("A", "D", "quarter"), "D"),
    (("C", "D", "x"), ("D", "B", "half"), ("B", "A", "half"), ("A", "C", "quarter"), ("C", "B", "half"), "B"),
    (("A", "B", "x"), ("conditional", "B", "C", "y"), ("C", "D", "half"), ("D", "A", "quarter"), "A"),
)


def amount_of(kind, balance, params):
    if kind in ("x", "y", "z"):
        return params[kind]
    return balance // {"half": 2, "third": 3, "quarter": 4}[kind]


def independent_state_solver(initial, params, events):
    """Reinterpret the declarative events without using the generated ledger."""
    names = "ABCD"
    balances = tuple(initial[name] for name in names)
    event_amounts = []
    for event in events:
        if event[0] == "conditional":
            _, left, right, key = event
            forward = balances[names.index(left)] >= params["threshold"]
            source, destination = (left, right) if forward else (right, left)
            moved = params[key]
        else:
            source, destination, key = event
            moved = (params[key] if key in params else
                     balances[names.index(source)] // {"half": 2, "third": 3,
                                                       "quarter": 4}[key])
        old = balances
        balances = tuple(value - moved * (name == source)
                         + moved * (name == destination)
                         for name, value in zip(names, old))
        assert min(balances) >= 0
        event_amounts.append((source, destination, moved))
    return dict(zip(names, balances)), event_amounts


def state_case(rng, pattern, variant):
    initial = {name: rng.randint(75, 125) for name in "ABCD"}
    params = {key: rng.randint(4, 12) for key in "xyz"}
    params["threshold"] = initial["B"] + params["x"] + (-3 if variant == 1 else 3)
    specification = STATE_PATTERNS[pattern - 1]
    events = specification[:-1]
    target = specification[-1]
    state = initial.copy()
    ledger = []
    sentences = []
    for event in events:
        if event[0] == "conditional":
            _, src, dst, kind = event
            condition = state[src] >= params["threshold"]
            actual_src, actual_dst = (src, dst) if condition else (dst, src)
            amount = params[kind]
            sentences.append(
                f"if {src} holds at least {params['threshold']} tokens at that point, {src} sends {amount} tokens to {dst}; "
                f"otherwise {dst} sends {amount} tokens to {src}")
        else:
            src, dst, kind = event
            actual_src, actual_dst = src, dst
            amount = amount_of(kind, state[src], params)
            wording = {"half": "half", "third": "one third", "quarter": "one quarter"}.get(kind)
            if wording:
                sentences.append(f"{src} sends {wording} of its then-current tokens to {dst}, rounding down")
            else:
                sentences.append(f"{src} sends {amount} tokens to {dst}")
        assert 0 <= amount <= state[actual_src]
        state[actual_src] -= amount
        state[actual_dst] += amount
        ledger.append({"source": actual_src, "destination": actual_dst, "amount": amount,
                       "balances": state.copy()})
    independent = {}
    for name in "ABCD":
        independent[name] = (initial[name]
                             + sum(e["amount"] for e in ledger if e["destination"] == name)
                             - sum(e["amount"] for e in ledger if e["source"] == name))
    assert state == independent and sum(state.values()) == sum(initial.values())
    second_state, second_events = independent_state_solver(initial, params, events)
    assert state == second_state
    assert [(e["source"], e["destination"], e["amount"]) for e in ledger] == second_events
    question = ("Four storage rooms A, B, C, and D start with "
                + ", ".join(f"{initial[n]} tokens in {n}" for n in "ABCD")
                + ". In order, " + "; then ".join(sentences)
                + f". How many tokens are in room {target} at the end?")
    branch = f"-{'high' if variant == 1 else 'low'}" if pattern == 6 else ""
    return {"id": f"state-{pattern:02d}-{variant:02d}", "family": "state",
            "structure_id": f"development-state-{pattern:02d}{branch}", "question": question,
            "gold": state[target], "initial": initial, "parameters": params,
            "target": target, "ledger": ledger, "final": state}


def build_manifest(seed):
    rng = random.Random(seed)
    cases = [arithmetic_case(rng, pattern, variant)
             for pattern in range(1, 7) for variant in (1, 2)]
    cases += [state_case(rng, pattern, variant)
              for pattern in range(1, 7) for variant in (1, 2)]
    for case in cases:
        case["question_sha256"] = hashlib.sha256(case["question"].encode()).hexdigest()
    assert len({case["question_sha256"] for case in cases}) == len(cases)
    return {"kind": "reference_only_development", "schema_version": 2,
            "seed": seed, "system_prompt": PROMPT, "temperature": 0,
            "max_tokens": MAX_TOKENS, "parser": "last-numeric-token-on-normal-stop-v1",
            "reference_sha256": REFERENCE_SHA256,
            "notice": "Public development structures; exclude these and equivalents from sealed holdout",
            "cases": cases}


def request_json(url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_reference(args):
    manifest = json.loads(args.manifest.read_text())
    if manifest != build_manifest(manifest["seed"]):
        raise ValueError("development manifest is not the fixed generator output")
    if digest(args.model_file) != REFERENCE_SHA256:
        raise ValueError("model is not the pinned Q4_K_M development reference")
    if args.output.exists():
        raise FileExistsError(args.output)
    base = args.server_url.rstrip("/")
    if request_json(base + "/health").get("status") != "ok":
        raise RuntimeError("server is not healthy")
    models = request_json(base + "/v1/models")
    served_ids = {model.get("id") for model in models.get("data", [])}
    if served_ids.isdisjoint({str(args.model_file), str(args.model_file.resolve())}):
        raise ValueError("server model path does not match hashed reference path")
    meta = {"kind": "reference_only_development", "model_sha256": REFERENCE_SHA256,
            "manifest_sha256": digest(args.manifest), "server_models": models,
            "server_url": base, "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps({"meta": meta}) + "\n")
        for case in manifest["cases"]:
            payload = {"messages": [{"role": "system", "content": PROMPT},
                                    {"role": "user", "content": case["question"]}],
                       "temperature": 0, "max_tokens": MAX_TOKENS, "stream": False}
            start = time.monotonic()
            try:
                response = request_json(base + "/v1/chat/completions", payload, timeout=180)
                choice = response["choices"][0]
                record = {"id": case["id"], "content": choice["message"].get("content", ""),
                          "finish_reason": choice.get("finish_reason"),
                          "usage": response.get("usage"), "timings": response.get("timings"),
                          "wall_seconds": time.monotonic() - start}
            except Exception as exc:
                record = {"id": case["id"], "error": f"{type(exc).__name__}: {exc}",
                          "wall_seconds": time.monotonic() - start}
            stream.write(json.dumps(record) + "\n")
            stream.flush()
    print(f"completed {args.output}; sha256={digest(args.output)}", flush=True)


def score(args):
    manifest = json.loads(args.manifest.read_text())
    rows = [json.loads(line) for line in args.run.read_text().splitlines()]
    meta = rows.pop(0)["meta"]
    if (meta.get("kind") != "reference_only_development"
            or meta.get("manifest_sha256") != digest(args.manifest)
            or meta.get("model_sha256") != REFERENCE_SHA256):
        raise ValueError("run metadata mismatch")
    cases = manifest["cases"]
    if len(rows) != len(cases) or [r["id"] for r in rows] != [c["id"] for c in cases]:
        raise ValueError("case IDs mismatch")
    result = []
    for case, record in zip(cases, rows):
        content = record.get("content", "").strip()
        normal_stop = record.get("finish_reason") == "stop"
        hits = list(ANY_NUMBER.finditer(content)) if normal_stop else []
        answer = Decimal(hits[-1].group(1).replace(",", "")) if hits else None
        final_line = FINAL_LINE.search(content) if normal_stop else None
        strict_answer = (Decimal(final_line.group(1).replace(",", ""))
                         if final_line else None)
        result.append({"id": case["id"], "family": case["family"],
                       "structure_id": case["structure_id"], "gold": case["gold"],
                       "answer": str(answer) if answer is not None else None,
                       "correct": answer == Decimal(case["gold"]),
                       "strict_answer": (str(strict_answer)
                                         if strict_answer is not None else None),
                       "strict_correct": strict_answer == Decimal(case["gold"]),
                       "normal_stop": normal_stop,
                       "format_compliant": final_line is not None,
                       "completion_tokens": (record.get("usage") or {}).get("completion_tokens"),
                       "wall_seconds": record.get("wall_seconds"), "error": record.get("error")})
    summary = {family: {"correct": sum(r["correct"] for r in result if r["family"] == family),
                        "strict_correct": sum(r["strict_correct"] for r in result
                                              if r["family"] == family),
                        "format_compliant": sum(r["format_compliant"] for r in result
                                                if r["family"] == family),
                        "n": sum(r["family"] == family for r in result),
                        "structure_success": {sid:
                            sum(r["correct"] for r in result if r["structure_id"] == sid)
                            for sid in sorted({r["structure_id"] for r in result
                                               if r["family"] == family})}}
               for family in ("arithmetic", "state")}
    write_new(args.output, {"kind": "reference_only_development_result",
                            "manifest_sha256": digest(args.manifest),
                            "run_sha256": digest(args.run), "summary": summary, "cases": result})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--manifest", type=Path, required=True)
    gen.add_argument("--seed", type=int, default=20261113)
    run = sub.add_parser("run-reference")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--server-url", required=True)
    run.add_argument("--model-file", type=Path, required=True)
    scored = sub.add_parser("score")
    scored.add_argument("--manifest", type=Path, required=True)
    scored.add_argument("--run", type=Path, required=True)
    scored.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        write_new(args.manifest, build_manifest(args.seed))
    elif args.command == "run-reference":
        run_reference(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
