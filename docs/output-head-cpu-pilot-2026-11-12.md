# Output-head CPU pilot

Design recorded 2026-11-12 18:42 EST, before building or scoring this candidate. This is a second exploratory arm in the general-purpose model-efficiency study. It is not an original algorithm or a sealed quality test.

## Hypothesis and prior art

The fresh same-base Qwen2.5-1.5B-Instruct Q4_K_M reference has one `output.weight` tensor of shape 151,936 by 1,536 at Q6_K, occupying 191,439,360 payload bytes. At Q4_K its payload arithmetic is 131,272,704 bytes, a possible 60,166,656-byte or 5.38% whole-file saving before export. The hypothesis is that reducing only this head to Q4_K can improve complete file bytes, process and cgroup peak memory, and full-request CPU-seconds under a fixed `--no-repack` CPU configuration while maintaining a prespecified benign task-quality bound.

This allocation idea has direct prior art. [Muse Glimmer](https://arxiv.org/html/2610.24628v3) explicitly reduces a Q4KM-like output projection from Q6_K to Q5_K and searches per-tensor Q4_K/Q5_K/Q6_K assignments using calibration loss, on another model and backend. [SoftWater](https://arxiv.org/html/2608.12026v1) allocates output-head rates by token class. [Softmax Reparameterization](https://arxiv.org/html/2609.31291) and [ARCHead](https://arxiv.org/html/2608.02703) study output-head quality recovery. These do not establish the joint CPU GGUF result for the pinned artifact. A successful local pilot would be deployment evidence, not a new compression method.

## Frozen construction and checks

Use the verified official FP16 input SHA-256 `fc89e330deb3fd8fa560f1c0f35a1e2b8da96d59e13445559ed190307a6f5649` and fresh Q4_K_M reference SHA-256 `b66e0350b994a95e26e9c41f05410c39f1ec84838b96144f494f87a5aaee8bf5` from [the first pilot](same-base-quantization-pilot-2026-11-12.md). Quantize with pinned llama.cpp b12283 binary SHA-256 `3cb6b1ea8dceca57ae32287b2c91229ff83df127d263becb498d6ee9dd6bdaf1`, Q4_K_M base mode, and [this exact-name rule file](../data/output-head-pilot-rules-2026-11-12.txt). Every quantized tensor is explicitly assigned its reference type except `output.weight=q4_k`, placed last because the quantizer's substring rule matcher can otherwise affect `attn_output.weight`. Inspect all names, shapes, types, and unchanged-type payloads after export. Reject a mismatched map or load error.

First use the same 200 public GSM8K questions and frozen answer parser as the other pilot, with the same reference outputs, temperature zero, 256-token cap, and no retries. This is a **shared public development diagnostic** across multiple candidate arms; its statistical interval does not compensate for model selection. Even a passing public result requires an independently sealed multistep suite with absolute and paired success bounds before a quality-preservation claim. Do not change rules after seeing this diagnostic and call the retuned result confirmatory.

For the resource screen, use the first pilot's exact runtime build and five alternating fresh-process pairs at 128/64 and 512/128 synthetic prompt/output sizes, four CPU threads, CPU only, `mmap`, `--poll 0`, and `--repack 0` for both files. Record exact artifact and companion bytes, model-process user plus system CPU-seconds, process VmHWM, wall time, faults and achieved token counts. A separate cold ext4-backed cgroup test must verify page ownership before reporting `memory.peak`. A CPU, RAM, or quality failure remains a negative finding. Run these screens without contention from another local benchmark.

## Status

The rule file is frozen. Candidate quantization, realized-map audit, quality and resource screens are pending. The theoretical saving is not an observed result.

### 2026-11-12 19:15 EST amendment, before construction

The shared 200-question diagnostic described above has now been scored on the reference and 14-tensor candidate. It failed its absolute-quality gate for both arms: the required `####` output line was usually absent, even in normally stopped responses. That scoring rule measures formatting as well as arithmetic and is unsuitable for ranking further candidates. Preserve the original diagnostic and raw outputs as a negative measurement. Do not use those same 200 questions with a revised prompt or parser as a confirmatory quality result. Before evaluating this output-head arm, freeze a disjoint question set, prompt, extraction rule, token cap, sample size, and paired decision rule. Report format compliance separately from task correctness. A public follow-up remains exploratory until an independent sealed multistep suite is run.

### 2026-11-12 19:24 EST simple-control amendment, before direct comparison

The same-source Q4_K_S file is the closest simple control for this output-head candidate. After the Q4_K_M resource screen, run five alternating fresh-process 512/128 no-repack pairs comparing Q4_K_S directly with the output-head file. Use the same binary, host, four threads, synthetic token workload, and measurements as above. If the output-head file is slower than Q4_K_S, do not describe it as a resource-dominating candidate even if it improves on Q4_K_M.

### 2026-11-12 19:25 EST resource screen

The realized output-head artifact is 1,057,154,080 bytes, SHA-256 `8efa8dfacf9e7dab4f5cfa16a26a1468d44eea70ac79f8b90e49a15d7806ceee`. Its [tensor audit](../data/output-head-q4-pinned-map-2026-11-12.json) found the same 339 tensor names and shapes as the fresh Q4_K_M reference. Only `output.weight` changed type, from Q6_K to Q4_K. All 338 other tensor payloads and all 29 GGUF metadata fields were byte-identical. The complete file saves exactly 60,166,656 bytes, or 5.38% of the Q4_K_M file. Against Q4_K_S, it saves 14,430,720 bytes, or 1.35%.

The [128/64 Q4_K_M pairs](../data/output-head-vs-q4km-no-repack-128-64-runs-2026-11-12.json) had median model-process CPU time of 11.3642 seconds for Q4_K_M and 10.5042 for output-head Q4, with median process peak RSS of 1,211,052,032 and 1,151,365,120 bytes. Candidate CPU time and RSS were lower in all five pairs. The [512/128 Q4_K_M pairs](../data/output-head-vs-q4km-no-repack-512-128-runs-2026-11-12.json) had median CPU time of 27.8130 versus 25.6887 seconds, and median RSS of 1,278,074,880 versus 1,217,818,624 bytes. Again, both candidate measurements were lower in all five pairs.

The [direct 512/128 Q4_K_S pairs](../data/output-head-vs-q4ks-no-repack-512-128-runs-2026-11-12.json) had median CPU time of 26.0890 seconds for Q4_K_S and 25.5680 for output-head Q4, and median process peak RSS of 1,225,330,688 versus 1,211,023,360 bytes. Candidate CPU time and RSS were lower in all five pairs. These are warm-cache synthetic prompt/generation screens on one Intel i7-12700K host, with `--repack 0`. They do not measure task correctness or establish a quality-preserving result.

The first cold-cgroup attempt failed its predeclared admission gate on the first reference run because `pgscan` increased by 1,041 pages. Its [rejected raw record](../data/frontier-cpu-head-cold-cgroup-pilot-attempt1-rejected-2026-11-12.json) is retained. The [fresh-inode rerun](../data/frontier-cpu-head-cold-cgroup-pilot-2026-11-12.json) admitted all ten processes with zero prelaunch model-page residency, a passing model-page charge-ownership check, and no swap, reclaim, OOM, or limit events. In all five 512/128 no-repack pairs, the candidate used fewer child CPU-seconds, lower peak process RSS, and lower fresh-cgroup `memory.peak`. Median paired candidate-minus-reference differences were -0.790 CPU-seconds, -60,043,264 process-RSS bytes, and -60,215,296 cgroup-peak bytes. This is a controlled cold synthetic resource result on one host. Held-out benign task quality remains pending.
