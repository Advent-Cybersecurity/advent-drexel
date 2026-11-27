# Lossless compression of two local model files

**Measured:** 2026-11-11, about 05:33 EST. **Scope:** Storage compression of benign model files. This study did not test malware, detection, or model quality.

## Answer

A ZIP-like archive can preserve a model file exactly while reducing its stored size. On the two Q4_K_M GGUF files previously benchmarked here, three standard lossless settings saved **2.26% to 2.94%**. Every decompressed file matched the original SHA256 hash and byte count. This is an exact copy of the *current GGUF*, not a recovery of the full-precision model from which Q4_K_M was made.

The archive does **not** by itself lower the RAM or CPU required by `llama.cpp` inference. The compressed file must be restored to GGUF bytes before the existing runtime loads it. Restoration adds CPU work and a small, temporary decompressor process. `llama.cpp` documents GGUF model loading and memory-mapped access, while its quantization documentation explains that lower precision can reduce size with possible accuracy loss. [Model loading](https://github.com/ggml-org/llama.cpp/blob/master/docs/models.md), [load modes](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md), [quantization](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md).

## Method

The inputs were the same official [Qwen2.5 0.5B](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67) and [Qwen2.5 1.5B](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9) Q4_K_M files used in the [earlier inference study](inference-resource-study-2026-11-11.md). The inputs were on `/tmp` tmpfs. Compressed files and restored files were written to `/var/tmp` on ext4, then removed. The three settings were Zstandard 1.5.7 levels 3 and 9 with one compression worker, and gzip 1.13 level 6. Zstandard and gzip are lossless codecs; Zstandard documents a configurable compression speed and ratio tradeoff. [Zstandard project documentation](https://github.com/facebook/zstd).

The [script](../scripts/run_lossless_compression_study.py) recorded compressed size, compression and decompression wall and CPU time, and sampled process peak RSS. CPU seconds sum work across process threads and can exceed elapsed wall seconds. It hashed each restored file and compared the result and byte count with the original. There was one run per model and setting. The measured times include local file I/O and may vary with cache and machine load. Process RSS was sampled about every 20 ms, so brief peaks may be missed.

## Results

| Model | Codec | Original bytes | Archived bytes | Storage saved | Compression CPU s | Restoration CPU s | Exact restore |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0.5B Q4_K_M | zstd 3 | 491,400,032 | 477,420,582 | 2.84% | 1.53 | 0.57 | Yes |
| 0.5B Q4_K_M | zstd 9 | 491,400,032 | 476,950,402 | 2.94% | 1.93 | 0.49 | Yes |
| 0.5B Q4_K_M | gzip 6 | 491,400,032 | 476,965,740 | 2.94% | 10.60 | 2.58 | Yes |
| 1.5B Q4_K_M | zstd 3 | 1,117,320,736 | 1,092,102,183 | 2.26% | 3.58 | 1.57 | Yes |
| 1.5B Q4_K_M | zstd 9 | 1,117,320,736 | 1,090,861,351 | 2.37% | 4.13 | 1.63 | Yes |
| 1.5B Q4_K_M | gzip 6 | 1,117,320,736 | 1,091,334,207 | 2.33% | 24.93 | 5.98 | Yes |

The best measured archived sizes were 454.86 MiB for the 0.5B file and 1,040.33 MiB for the 1.5B file, saving 13.78 MiB and 25.23 MiB. Level 9 saved only another 0.10 and 0.11 percentage points over level 3, respectively. The sampled decompressor peak RSS was about 8 to 10 MiB for zstd and about 2 MiB for gzip. Those figures describe the restoration utility, **not** inference RAM. The earlier inference test measured about 570 and 1,752 MiB median sampled peak RSS for the 128/64 token workload with the unarchived files.

## What remains possible

1. **Exact current model, smaller distribution file:** Achieved, but the measured saving is modest. Restoring the original GGUF returns the same bytes and the same model representation. Inference CPU and RAM would still need separate measurement under the chosen loading workflow.
2. **Exact current model, lower active RAM:** A different loader could decompress weights on demand or stage them outside resident memory. This study did not implement that loader. It would need to preserve GGUF tensor bytes, then measure peak memory, page faults, CPU time, and token latency. For a dense model that uses its layers repeatedly during generation, repeated restoration may exchange RAM use for CPU and latency. That is a design hypothesis, not a measured result here.
3. **Much smaller weights or lower inference cost:** Lower-bit quantization, pruning, and distillation change the model representation or behavior. They can be evaluated for acceptable *task-level* quality, but a finite benchmark cannot guarantee every capability or identical outputs. The tested Q4_K_M files are already quantized, so an additional quantization step would require a defined quality tolerance and evaluation set. [llama.cpp quantization documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md).

The next useful decision is whether “retain all inference” means an identical model file, identical outputs under a specified deterministic runtime, or comparable performance on a specified set of tasks. The first is verified here. The second would need output comparison under fixed runtime settings. The third permits larger changes but requires explicit quality tests.

## Data and reproduction

The [raw JSON](../data/lossless-compression-study-2026-11-11.json) contains the exact file sizes, hashes, commands, timing, process RSS samples, and exit codes. Neither model weights nor compressed archives are committed. With the two pinned GGUF files and `zstd`, `gzip`, Python, and `psutil` installed, run `python3 scripts/run_lossless_compression_study.py --help` for the arguments.
