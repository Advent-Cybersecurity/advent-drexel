#!/usr/bin/env python3
"""Public, reference-only structural-grammar calibration; no candidate path exists."""

import argparse
import hashlib
import itertools
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
MAX_TOKENS = 1536
ANY_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?(?![A-Za-z])")
FINAL_LINE = re.compile(r"(?:^|\n)The final answer is\s+([-+]?\d[\d,]*)\.?(?:\s*)\Z")
MARKER = re.compile(r"The final answer is\s+[-+]?\d[\d,]*", re.I)
ROOMS = "ABCD"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"wrote {path}; sha256={digest(path)}", flush=True)


def arithmetic_replay(initial, events):
    """Immutable-state interpreter, separate from the mutable generator loop."""
    state = (initial, 0)
    trace = []
    for event in events:
        active, reserve = state
        op = event["op"]
        if op == "consume":
            state = (active - event["amount"], reserve)
        elif op == "reserve":
            moved = active // event["divisor"]
            state = (active - moved, reserve + moved)
        elif op == "release":
            moved = reserve // event["divisor"]
            state = (active + moved, reserve - moved)
        elif op == "receive":
            state = (active + event["packs"] * event["per_pack"], reserve)
        elif op == "conditional":
            gain = (event["packs"] * event["per_pack"]
                    if active >= event["threshold"] else event["otherwise"])
            state = (active + gain, reserve)
        else:
            raise ValueError(op)
        assert min(state) >= 0
        trace.append(list(state))
    return state, trace


def arithmetic_case(rng, index, length):
    first_packs, first_per_pack = rng.randint(5, 10), rng.randint(7, 11)
    second_packs, second_per_pack = rng.randint(3, 7), rng.randint(5, 9)
    first = first_packs * first_per_pack
    second = second_packs * second_per_pack
    initial = first + second
    # Every draw has a conditional and a reserve/release dependency. Extras vary
    # operator order; draw rejection here uses structure only, not model output.
    ops = ["reserve", "release", "conditional", "consume"]
    ops += [rng.choice(("consume", "receive", "reserve", "release"))
            for _ in range(length - len(ops))]
    for _ in range(100):
        rng.shuffle(ops)
        if (ops.index("reserve") < ops.index("release")
                and any(op == "reserve" for op in ops[:ops.index("release")])):
            break
    else:
        raise RuntimeError("failed to order reserve and release")
    active, reserve = initial, 0
    events, sentences, trace = [], [], []
    for op in ops:
        if op == "consume":
            amount = rng.randint(3, 11)
            active -= amount
            event = {"op": op, "amount": amount}
            sentence = f"use {amount} items from active stock"
        elif op == "reserve":
            divisor = rng.choice((2, 3, 4))
            moved = active // divisor
            active -= moved
            reserve += moved
            event = {"op": op, "divisor": divisor}
            sentence = (f"move one item from every complete group of {divisor} in the then-current "
                        "active stock into reserve, pooling all active items before grouping")
        elif op == "release":
            divisor = rng.choice((2, 3, 4))
            moved = reserve // divisor
            active += moved
            reserve -= moved
            event = {"op": op, "divisor": divisor}
            sentence = (f"move one item from every complete group of {divisor} in the then-current "
                        "reserve back into active stock, pooling all reserved items before grouping")
        elif op == "receive":
            packs, per_pack = rng.randint(2, 5), rng.randint(5, 11)
            active += packs * per_pack
            event = {"op": op, "packs": packs, "per_pack": per_pack}
            sentence = f"add {packs} packs of {per_pack} items each to active stock"
        elif op == "conditional":
            threshold = active + rng.choice((-4, 4))
            packs, per_pack, otherwise = rng.randint(2, 4), rng.randint(5, 10), rng.randint(3, 8)
            branch = "high" if active >= threshold else "low"
            active += packs * per_pack if branch == "high" else otherwise
            event = {"op": op, "threshold": threshold, "packs": packs,
                     "per_pack": per_pack, "otherwise": otherwise, "branch": branch}
            sentence = (f"if active stock holds at least {threshold} items at that point, "
                        f"add {packs} packs of {per_pack} items each to active stock; "
                        f"otherwise add exactly {otherwise} loose items to active stock")
        else:
            raise ValueError(op)
        assert active >= 0 and reserve >= 0
        events.append(event)
        sentences.append(sentence)
        trace.append([active, reserve])
    replay, replay_trace = arithmetic_replay(initial, events)
    assert replay == (active, reserve) and replay_trace == trace
    signature = tuple((e["op"], e.get("divisor", 0), e.get("branch", ""))
                      for e in events)
    structure_id = "arithmetic-" + hashlib.sha256(repr(signature).encode()).hexdigest()[:16]
    question = (f"An inventory receives {first_packs} packs of {first_per_pack} items each and "
                f"{second_packs} packs of {second_per_pack} items each, all pooled in active stock; "
                "reserve starts at zero. "
                "In the following order, " + "; then ".join(sentences)
                + ". Items left in an incomplete group stay where they are. "
                "How many items are in active stock at the end?")
    return {"id": f"arithmetic-{index:02d}", "family": "arithmetic",
            "length": length, "structure_id": structure_id, "signature": signature,
            "question": question, "gold": active, "initial": initial,
            "events": events, "trace": trace, "final": {"active": active, "reserve": reserve}}


def state_replay(initial, events):
    """Immutable tuple implementation of the event semantics."""
    state = tuple(initial[name] for name in ROOMS)
    trace = []
    for event in events:
        source, destination = event["source"], event["destination"]
        if event["op"] == "conditional":
            if state[ROOMS.index(source)] < event["threshold"]:
                source, destination = destination, source
            moved = event["amount"]
        elif event["op"] == "fixed":
            moved = event["amount"]
        else:
            moved = state[ROOMS.index(source)] // event["divisor"]
        assert moved <= state[ROOMS.index(source)]
        state = tuple(value - moved * (name == source) + moved * (name == destination)
                      for name, value in zip(ROOMS, state))
        assert min(state) >= 0
        trace.append(list(state))
    return dict(zip(ROOMS, state)), trace


def canonical_state(events, target):
    """Isomorphism ID under all four-room renamings, retaining event order."""
    candidates = []
    for names in itertools.permutations(ROOMS):
        mapping = dict(zip(ROOMS, names))
        signature = tuple((e["op"], mapping[e["source"]], mapping[e["destination"]],
                           e.get("divisor", 0), e.get("branch", "")) for e in events)
        candidates.append((signature, mapping[target]))
    canonical = min(candidates)
    return "state-" + hashlib.sha256(repr(canonical).encode()).hexdigest()[:16], canonical


def state_case(rng, index, length):
    initial = {name: rng.randint(90, 145) for name in ROOMS}
    balances = initial.copy()
    events, sentences, trace = [], [], []
    prior_destination = rng.choice(ROOMS)
    for position in range(length):
        if position == 0 or rng.random() < 0.72:
            source = prior_destination
        else:
            source = rng.choice(ROOMS)
        destination = rng.choice([name for name in ROOMS if name != source])
        op = "conditional" if position == length // 2 else rng.choice(("fraction", "fraction", "fixed"))
        if op == "conditional":
            threshold = balances[source] + rng.choice((-5, 5))
            amount = rng.randint(4, 11)
            branch = "high" if balances[source] >= threshold else "low"
            actual_source, actual_destination = ((source, destination) if branch == "high"
                                                 else (destination, source))
            event = {"op": op, "source": source, "destination": destination,
                     "threshold": threshold, "amount": amount, "branch": branch}
            sentence = (f"if room {source} holds at least {threshold} items at that point, "
                        f"room {source} sends {amount} items to room {destination}; "
                        f"otherwise room {destination} sends {amount} items to room {source}")
        elif op == "fixed":
            amount = rng.randint(4, 11)
            actual_source, actual_destination = source, destination
            event = {"op": op, "source": source, "destination": destination, "amount": amount}
            sentence = f"room {source} sends {amount} items to room {destination}"
        else:
            divisor = rng.choice((2, 3, 4))
            amount = balances[source] // divisor
            actual_source, actual_destination = source, destination
            event = {"op": op, "source": source, "destination": destination,
                     "divisor": divisor}
            sentence = (f"room {source} sends one item for every complete group of {divisor} "
                        f"items it holds at that point to room {destination}, rounding down")
        assert amount <= balances[actual_source]
        balances[actual_source] -= amount
        balances[actual_destination] += amount
        events.append(event)
        sentences.append(sentence)
        trace.append([balances[name] for name in ROOMS])
        prior_destination = actual_destination
    target = prior_destination
    replay, replay_trace = state_replay(initial, events)
    assert replay == balances and replay_trace == trace
    assert sum(initial.values()) == sum(balances.values())
    structure_id, signature = canonical_state(events, target)
    question = ("Four storage rooms start with "
                + ", ".join(f"{initial[name]} items in room {name}" for name in ROOMS)
                + ". In the following order, " + "; then ".join(sentences)
                + f". How many items are in room {target} at the end?")
    return {"id": f"state-{index:02d}", "family": "state", "length": length,
            "structure_id": structure_id, "signature": signature,
            "question": question, "gold": balances[target], "initial": initial,
            "events": events, "trace": trace, "target": target, "final": balances}


def build_manifest(seed):
    rng = random.Random(seed)
    cases, seen = [], set()
    for family, maker in (("arithmetic", arithmetic_case), ("state", state_case)):
        for index in range(1, 13):
            length = 4 if index <= 6 else 7
            for _ in range(500):
                case = maker(rng, index, length)
                if case["structure_id"] not in seen:
                    break
            else:
                raise RuntimeError("failed to draw unique public development structure")
            seen.add(case["structure_id"])
            case["question_sha256"] = hashlib.sha256(case["question"].encode()).hexdigest()
            cases.append(case)
    assert len(cases) == 24 and len(seen) == 24
    assert len({case["question_sha256"] for case in cases}) == 24
    return {"kind": "reference_only_public_development", "schema_version": 3,
            "seed": seed, "system_prompt": PROMPT, "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "parser": "last-numeric-token-on-normal-stop-v1",
            "reference_sha256": REFERENCE_SHA256,
            "notice": "Exclude these structures, their isomorphs, and functional equivalents from sealed tests",
            "cases": cases}


def request_json(url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_reference(args):
    manifest = json.loads(args.manifest.read_text())
    if manifest != json.loads(json.dumps(build_manifest(manifest["seed"]), sort_keys=True)):
        raise ValueError("manifest mismatch")
    if digest(args.model_file) != REFERENCE_SHA256:
        raise ValueError("not the pinned reference model")
    if args.output.exists():
        raise FileExistsError(args.output)
    base = args.server_url.rstrip("/")
    if request_json(base + "/health").get("status") != "ok":
        raise RuntimeError("server not healthy")
    ids = {m.get("id") for m in request_json(base + "/v1/models").get("data", [])}
    if ids.isdisjoint({str(args.model_file), str(args.model_file.resolve())}):
        raise ValueError("server model path differs")
    meta = {"kind": manifest["kind"], "model_sha256": REFERENCE_SHA256,
            "manifest_sha256": digest(args.manifest), "server_url": base,
            "run_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps({"meta": meta}) + "\n")
        for case in manifest["cases"]:
            payload = {"messages": [{"role": "system", "content": PROMPT},
                                    {"role": "user", "content": case["question"]}],
                       "temperature": 0, "max_tokens": MAX_TOKENS, "stream": False}
            start = time.monotonic()
            try:
                response = request_json(base + "/v1/chat/completions", payload, timeout=240)
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
    if (meta["kind"] != manifest["kind"]
            or meta["manifest_sha256"] != digest(args.manifest)
            or meta["model_sha256"] != REFERENCE_SHA256):
        raise ValueError("run metadata mismatch")
    cases = manifest["cases"]
    if len(rows) != len(cases) or [r["id"] for r in rows] != [c["id"] for c in cases]:
        raise ValueError("case mismatch")
    result = []
    for case, record in zip(cases, rows):
        content = record.get("content", "").strip()
        normal = record.get("finish_reason") == "stop"
        hits = list(ANY_NUMBER.finditer(content)) if normal else []
        answer = Decimal(hits[-1].group(0).replace(",", "")) if hits else None
        terminal = FINAL_LINE.search(content) if normal else None
        terminal_answer = Decimal(terminal.group(1).replace(",", "")) if terminal else None
        markers = MARKER.findall(content)
        result.append({"id": case["id"], "family": case["family"],
                       "length": case["length"], "structure_id": case["structure_id"],
                       "gold": case["gold"], "answer": str(answer) if answer is not None else None,
                       "correct": answer == Decimal(case["gold"]),
                       "terminal_correct": terminal_answer == Decimal(case["gold"]),
                       "exactly_one_terminal_correct": (len(markers) == 1
                                                        and terminal_answer == Decimal(case["gold"])),
                       "normal_stop": normal, "marker_count": len(markers),
                       "completion_tokens": (record.get("usage") or {}).get("completion_tokens"),
                       "wall_seconds": record.get("wall_seconds"), "error": record.get("error")})
    summary = {family: {"n": sum(r["family"] == family for r in result),
                        "correct": sum(r["correct"] for r in result if r["family"] == family),
                        "terminal_correct": sum(r["terminal_correct"] for r in result
                                                if r["family"] == family),
                        "exactly_one_terminal_correct": sum(r["exactly_one_terminal_correct"]
                                                            for r in result if r["family"] == family),
                        "cap_stops": sum(not r["normal_stop"] and not r["error"] for r in result
                                         if r["family"] == family),
                        "transport_errors": sum(bool(r["error"]) for r in result
                                                if r["family"] == family)}
               for family in ("arithmetic", "state")}
    write_new(args.output, {"kind": "reference_only_public_development_result",
                            "manifest_sha256": digest(args.manifest),
                            "run_sha256": digest(args.run), "summary": summary,
                            "cases": result})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--manifest", type=Path, required=True)
    gen.add_argument("--seed", type=int, default=2026111303)
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
