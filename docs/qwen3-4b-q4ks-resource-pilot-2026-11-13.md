# Qwen3-4B Q4_K_S resource control

**Status, 2026-11-13:** Exploratory CPU pilot on two third-party GGUF releases. The Q4_K_S file is smaller and matched the Q4_K_M reference on 16 reused public development questions. Its warm process-RAM result depends on the repack setting: it increases with default repacking and decreases without repacking. No admitted cold paired result, complete installed-package count, full served-task CPU result, or sealed quality comparison exists.

## Artifacts and workload

Both files come from the pinned [Bartowski Qwen3-4B-Instruct-2507 GGUF revision](https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/tree/ae44f08e1392f39c0e474af10c3ff8355c8b6688). The Q4_K_M reference is 2,497,280,736 bytes with SHA-256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`; Q4_K_S is 2,383,309,536 bytes with SHA-256 `952af947c6aabf7b72f7d8e279e76f7bf4b0d12431eb3abb588ef312865622d8`. The complete GGUF file saving is **113,971,200 bytes (4.56%)**. These two community artifacts are not a controlled export from one pinned official BF16 checkpoint.

The [warm paired harness](../scripts/run_same_base_quantization_pilot.py) uses pinned `llama.cpp` b12283 `llama-bench` (SHA-256 `c7b3aef28a858cf799babeb6afe5c6b9ded83a0e7d169a54b9f54d1b3051dc48`) on a 12th Gen Intel Core i7-12700K CPU, four threads, mmap, no benchmark warmup, 128 prompt tokens, and 64 generated tokens. Each arm is a fresh process; odd blocks run reference then candidate and even blocks reverse the order. Its `wait4` CPU time and peak RSS include process load and synthetic prefill and generation. Page cache is warm and uncontrolled. The reported process RSS excludes other processes and does not count all cgroup-charged file cache. This is a fixed-token synthetic workload, not the full sequence of a benign task.

## Default repacking: measured result

The [five-pair raw record](../data/frontier-cpu-qwen3-4b-q4ks-warm-pilot-2026-11-13.json), SHA-256 `661af71a322f07a771d71397cf4aa5c55146172b9d8b9a1cf78d1045dead655e`, used `--repack 1` for both arms. Candidate-minus-reference child CPU-seconds were -1.170, -0.369, -0.646, -0.730, and -0.270, with paired median **-0.646 seconds**. Candidate-minus-reference peak process RSS was +104,767,488, +104,476,672, +102,891,520, +104,185,856, and +84,471,808 bytes, with paired median **+104,185,856 bytes**. All five pairs show lower CPU time and higher peak process RSS. The paired median wall-time difference was -0.005 seconds, too small to interpret as a useful latency gain in this pilot.

The smaller Q4_K_S file therefore fails the measured peak process-RAM direction under this default-repack warm setting. The file and CPU observations do not compensate for the RAM regression under a joint four-gate decision.

## No repacking: measured result

A separate [five-pair warm record](../data/frontier-cpu-qwen3-4b-q4ks-warm-no-repack-pilot-2026-11-13.json), SHA-256 `d1de6a06943d2533a21e9188f7335371cd900ea994cca5342cf286909bd53264`, kept the same binary, artifacts, 128/64 token case, four threads, and alternating order, but set `--repack 0` on both arms. Candidate-minus-reference CPU-seconds were -1.989, -2.457, -2.514, -2.047, and -2.342, with paired median **-2.342 seconds**. Candidate-minus-reference process RSS was -114,204,672, -114,192,384, -113,434,624, -113,946,624, and -113,500,160 bytes, with paired median **-113,946,624 bytes**. All five pairs favor Q4_K_S on both counters. The paired median wall-time difference was -0.613 seconds.

The sign of the process-RAM result changes with the repack setting. This is an observed runtime interaction, not a traced per-tensor allocation mechanism. A no-repack memory advantage cannot be combined with a default-repack reference arm in a claimed paired deployment result. The public quality screen used a no-repack server, so the no-repack resource setting is its closer workload match, although the benchmark's 128/64 synthetic request is still different from those quality requests.

## Tensor layout audit

The [descriptor audit](../data/frontier-cpu-qwen3-4b-q4ks-tensor-topology-2026-11-13.json), SHA-256 `3179734acd1f6e0f51ef1c622eac07a2db93dbb1a981cc23052ae802a4a4f54a`, read GGUF tensor names, shapes, types, and packed sizes without comparing payload bytes. Both files contain the same 398 tensor names and shapes. The 36 changed descriptors are 18 `attn_v.weight` and 18 `ffn_down.weight` tensors: 8 change from Q6_K to Q5_K, and 28 from Q6_K to Q4_K. Their packed-byte difference exactly accounts for the 113,971,200-byte file difference. The tied Q6_K embedding is unchanged. More Q4_K tensors may change the runtime's repacked allocation, but this audit does not trace allocations or establish the cause of the observed RAM reversal.

## Cold trial admission

The [default-repack cold-cgroup attempt](../data/frontier-cpu-qwen3-4b-q4ks-cold-cgroup-2026-11-13.json) stopped at its first Q4_K_M arm under the pre-existing zero-reclaim admission rule. The trial used a new ext4 inode, verified its hash, found zero resident model pages before launch, and supported simultaneous file-page charge ownership. The fresh scope nevertheless recorded 1,114 pages scanned and 79 stolen during the run, so the harness rejected the trial. A separate [no-repack attempt](../data/frontier-cpu-qwen3-4b-q4ks-cold-no-repack-cgroup-2026-11-13.json) likewise stopped at its first reference arm after 1,106 pages scanned and 75 stolen. Both first-arm process and cgroup peaks are diagnostic only. Neither attempt ran a Q4_K_S cold arm, and there is **no accepted cold paired comparison**. The admission rule was not relaxed after either rejection.

## Remaining decision

The public [quality screen](qwen3-4b-development-screen-2026-11-13.md) gave both releases 8/8 arithmetic and 8/8 ordered-state correctness on reused templates. It cannot show noninferiority on unseen dependency structures. A supported deployment comparison needs admitted cold process and cgroup peaks, complete installed bytes, full-request CPU including generated-token and retry differences, and sealed dependent-step quality under one fixed repack policy. A custom compression method must be compared with this simple Q4_K_S control on those same measures.
