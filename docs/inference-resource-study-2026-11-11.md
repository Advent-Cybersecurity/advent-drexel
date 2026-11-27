# Benign local inference resource study

**Measured:** 2026-11-11, 05:26 to 05:28 EST. **Status:** Completed on one CPU-only virtual machine.

## Question and result

How much storage, resident memory, CPU time, and wall time did two small local models require for fixed, benign inference workloads on this machine? Both models completed every measured run. For a 128-token prompt plus 64 generated tokens, the smaller model's median sampled peak resident memory was **570 MiB** and median process wall time was **1.68 seconds**. The larger model used **1,752 MiB** and **3.83 seconds**. For a 512-token prompt plus 128 generated tokens, the figures were **605 MiB / 3.67 seconds** and **1,809 MiB / 8.09 seconds**, respectively.

These are local resource measurements. They do not measure whether any security product would alert on inference, a download, or a code change. No endpoint alert telemetry was available in this VM.

## Setup

- Kali GNU/Linux Rolling, kernel `6.18.12+kali-amd64`, in VMware. The guest reported eight logical CPUs with an Intel Core i7-12700K model string, 15.7 GiB total RAM, and 0.93 GiB swap. The host CPU allocation and contention are unknown. The benchmark used four CPU threads and no GPU layers.
- [llama.cpp `llama-bench` release b12283](https://github.com/ggml-org/llama.cpp/releases/tag/b12283), build commit `f3b407ca1`, Ubuntu x64 CPU binary. Archive SHA256: `5f24a62b84a37c186efd1e3e1d77bfad3a1772d9aa35bfcc9e1572723d0c4faf`. `llama-bench` executable SHA256: `c7b3aef28a858cf799babeb6afe5c6b9ded83a0e7d169a54b9f54d1b3051dc48`.
- [Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67), revision `9217f5db79a29953eb74d5343926648285ec7e67`, Q4_K_M file, 491,400,032 bytes (469 MiB). File SHA256: `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.
- [Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9), revision `91cad51170dc346986eccefdc2dd33a9da36ead9`, Q4_K_M file, 1,117,320,736 bytes (1,066 MiB). File SHA256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.

The local file hashes matched the Qwen repositories' published LFS SHA256 values at those revisions. The model labels are nominal: `llama-bench` reported 630,167,424 and 1,777,088,000 parameters in the two loaded files.

## Method

The [measurement script](../scripts/run_inference_resource_study.py) launched one `llama-bench` process for each run, using `-p 0 -n 0 -pg 128,64` or `-pg 512,128`, `-r 1 -t 4 -ngl 0 -o json --no-warmup`. Each configuration had five separate process runs. The cases ran in repeated order: non-AI control, smaller model, larger model. The control hashed 2 GiB of repeated input with four Python SHA256 workers. Its purpose was to show a separate CPU-bound process measurement, not to represent equivalent useful work.

The script sampled process resident set size, thread count, and CPU time approximately every 50 ms. It recorded the largest sampled RSS and last sampled CPU time, so brief peaks could be missed. Wall time includes process startup, loading from local storage or cache, the benchmark, and shutdown. `llama-bench` inference time is its internal prompt-processing plus generation measurement. Its [documentation](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/llama-bench/README.md) says benchmark timings exclude tokenization and sampling. The model files had already been downloaded and hashed, which could warm the file cache. Download time and network traffic were outside the timed runs.

## Complete results

The table reports medians of five runs. Parentheses show the observed minimum and maximum process wall times. MiB uses 1,048,576 bytes. All 30 recorded processes exited successfully, with no malformed benchmark result.

| Process | Prompt / generation tokens | File size MiB | Peak RSS MiB | Wall seconds, median (range) | Benchmark inference seconds | CPU seconds, last sample |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Python SHA256 control | n/a | n/a | 17.9 | 0.31 (0.31 to 0.31) | n/a | 0.92 |
| Qwen2.5 0.5B Q4_K_M | 128 / 64 | 468.6 | 569.8 | 1.68 (1.58 to 1.84) | 1.46 | 5.98 |
| Qwen2.5 1.5B Q4_K_M | 128 / 64 | 1,065.6 | 1,751.7 | 3.83 (3.68 to 3.89) | 3.33 | 13.68 |
| Python SHA256 control | n/a | n/a | 18.0 | 0.31 (0.31 to 0.31) | n/a | 0.94 |
| Qwen2.5 0.5B Q4_K_M | 512 / 128 | 468.6 | 605.2 | 3.67 (3.66 to 3.77) | 3.47 | 14.11 |
| Qwen2.5 1.5B Q4_K_M | 512 / 128 | 1,065.6 | 1,809.5 | 8.09 (7.94 to 8.37) | 7.54 | 30.87 |

The larger model used about three times the sampled peak RSS of the smaller model for either workload. Its median process wall time was 2.28 times as long for the shorter workload and 2.20 times as long for the longer workload. The longer workload raised median RSS by 35 MiB for the smaller model and 58 MiB for the larger model, while roughly doubling wall time. These comparisons describe this exact quantization, runtime, machine, and token settings.

## Endpoint observation and limits

Package, process, and running-service checks did not identify an active ClamAV, Falco, auditd, osquery, Wazuh, CrowdStrike, SentinelOne, or Defender service. `kauditd` appeared as a kernel thread, but no alert source or policy was available. Those checks cannot exclude every monitoring product. **Detection outcome: not measured.** The study cannot estimate an alert probability or support the claim that a model download or inference run causes immediate detection.

These synthetic token workloads do not assess model output quality, benign code-revision success, a full application, background host activity, GPU use, energy, or a memory-constrained endpoint. Five runs per configuration describe observed variation here, not a population confidence interval. The next evidence needed is a benign code-revision success test at each resource budget and measurements on specified endpoint classes with recorded security policy and alert telemetry. No result here establishes the integrated malware behavior assessed by the [feasibility plan](feasibility-constraints-and-study-plan.md).

## Raw records and reproduction

Every run, including the control and its exit status, is in [128/64 raw JSON](../data/inference-resource-study-2026-11-11.json) and [512/128 raw JSON](../data/inference-resource-study-long-context-2026-11-11.json). Both files include software hashes, model sizes, host metadata, run order, timestamps, and process measurements. The model weights and runtime binary are not stored in this repository.

After obtaining and verifying the two pinned model files and the pinned `llama-bench` binary, run `scripts/run_inference_resource_study.py --help` for the arguments. Use the default token counts for the short workload and `--prompt-tokens 512 --generation-tokens 128` for the longer workload.
