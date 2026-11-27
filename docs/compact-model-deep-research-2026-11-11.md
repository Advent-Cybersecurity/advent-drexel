# Compact models and frontier capability: an evidence review

**Reviewed:** 2026-11-11. **Scope:** Benign model science, local inference resources, and evaluation. No model was trained and no new quality benchmark was run for this report.

## Research question and answer

Can a local model with a small file, low RAM use, and low CPU use retain all the inference capability of GPT-6 Astra or Claude Opus 5.5?

**The reviewed evidence does not show this today.** It does show substantial savings for a *specified task*, and large improvements in capability per parameter. Some compact models beat larger models on selected benchmarks. Those results cannot establish equivalence across unfamiliar tasks, coding, multimodal inputs, long context, tools, and reliability. Nor do they prove that a future compact architecture is impossible. The useful research target is a measured quality threshold on an explicit workload and device budget.

There are three different meanings of “retain capability”:

1. **Exact file restoration.** Lossless coding can restore the same model bytes. Identical output behavior still depends on the inference runtime, settings, and deterministic execution conditions. The current runtime requires decompression before it can use an archive. The initial [general-purpose archive experiment](lossless-model-compression-study-2026-11-11.md) saved 2.26% to 2.94% of the tested quantized files; a later [GGUF-aware storage check](compact-model-evidence-update-2026-11-11.md) saved more on the same files but did not establish inference savings.
2. **Statistical behavior.** A quantized or distilled model may produce similar answers on a defined distribution. Outputs can differ, and rare failures matter.
3. **Task-level performance.** A compact model or system can meet an acceptance threshold on a particular workload. This is the realistic engineering objective, but the workload and all external resources must be stated.

The service model weights for [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) and [Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview) are not supplied by their cited model pages as local artifacts. This study cannot measure their weight size, RAM, or CPU requirements directly. Their documented context capacities are 1,050,000 and 1,000,000 tokens respectively, and Anthropic documents image input for Opus 5.5. A local comparison must state whether those capabilities are required.

## What the newest compact models demonstrate

The following are vendor-reported numbers, not independent results from this repository. Scores should be compared within the same table and benchmark version, then verified on held-out tasks.

| Published example | What it demonstrates | What it leaves unresolved |
| --- | --- | --- |
| [Qwen3.5-4B model card](https://huggingface.co/Qwen/Qwen3.5-4B) | Qwen reports its 4B model at 79.1 on MMLU-Pro and 76.2 on GPQA Diamond, versus 74.8 and 71.5 for gpt-oss-20b in the same card. It supports text and vision and lists a 262K native context. | In that same card, Qwen reports LiveCodeBench v6 at 55.8 versus 74.6 and HMMT November 2025 at 76.8 versus 81.8. Selected wins do not imply broad parity. The comparison is against gpt-oss-20b, not GPT-6 Astra or Opus 5.5. |
| [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4) | Google reports E2B/E4B/31B scores of 60.0/69.4/85.2 on MMLU-Pro, 44.0/52.0/80.0 on LiveCodeBench v6, and 19.1/25.4/66.4 on MRCR v2 eight-needle 128K. Compact variants have useful abilities. | The same-card gap grows on harder coding and long-context tests. These are selected benchmark scores and do not establish universal ranking. |
| [gpt-oss architecture card](https://deploymentsafety.openai.com/gpt-oss/architecture) | The 20.91B-total, 3.61B-active mixture-of-experts model has a 12.8 GiB checkpoint. Active parameters can be far fewer than total parameters. | Expert weights still occupy storage. A low active count is not a 3.61B-parameter file or a guarantee of low RAM. It is not a direct GPT-6 Astra substitute. |
| [Gemma 4 overview](https://ai.google.dev/gemma/docs/core) | Google's estimated Q4_0 static loading for E2B, E4B, 26B A4B, and 31B is 2.9, 4.5, 14.4, and 17.5 GB on GPU/TPU, excluding software and context. The 26B A4B model activates about 3.8B of 25.2B parameters. | These are vendor estimates for a specified loading representation, not measured peak CPU VM RAM. The mixture-of-experts example again shows that active compute and stored weights are different quantities. |

The examples support an important but narrow conclusion: parameter count alone is an inadequate capability metric. Training data, architecture, post-training, context design, modality support, and test-time computation matter. The evidence still does not show a low-resource local model matching the named frontier services on a broad independent suite.

## The resource floor

For `P` parameters stored at a fixed `b` bits per value, the weight-value payload is `P × b / 8` bytes. A 4B model at fixed four-bit precision has a 2 GB decimal weight-value payload; a 20B model has 10 GB. Real files add scales, tensor metadata, and often mixed-precision tensors. Entropy coding can reduce stored bytes below that fixed-width payload when the values contain redundancy, but decoding may add work or require a larger live representation. Runtime memory also includes model structures, activations, attention state, and process overhead. These are arithmetic reference points, not universal lower bounds or predictions of peak memory.

If a model is entropy-coded more tightly on disk, the existing compute kernels still need a usable weight representation during inference. A new compressed-domain representation and matching kernels could trade decompression work, memory traffic, and random access against storage. It must be benchmarked as a new runtime design. The [local lossless study](lossless-model-compression-study-2026-11-11.md) restored byte-identical GGUF files but did not demonstrate lower RAM or CPU use during inference.

The repository's [CPU-only VM measurements](inference-resource-study-2026-11-11.md) provide a concrete baseline. With four CPU threads and Q4_K_M Qwen2.5 files, median sampled peak resident memory across five runs was 570 MiB for the 0.5B file and 1,752 MiB for the 1.5B file at 128 prompt and 64 generated tokens. Median wall time was 1.68 and 3.83 seconds. At 512 prompt and 128 generated tokens, peak memory was 605 and 1,809 MiB, with wall time 3.67 and 8.09 seconds. The files were 491,400,032 and 1,117,320,736 bytes. These measurements apply to this VM, runtime, and workload. Neither model underwent quality evaluation.

Memory and compute have different bottlenecks:

| Resource | Main drivers | Why a smaller file may not solve it |
| --- | --- | --- |
| Stored bytes | All weights, formats, metadata | CPU and RAM can rise during decoding, and lossy coding can change quality. |
| Peak RAM | Resident weights, activations, key-value cache, buffers, runtime | Context length and batch size change memory even with a fixed model file. |
| CPU work | Active operations, memory transfer, token count, kernels | Longer reasoning or an inefficient low-bit kernel can offset weight savings. |
| Latency | Prompt processing, generated tokens, scheduling, hardware | A faster per-token model can still take longer if it produces many more tokens. |

The correct resource record includes artifact bytes, peak RSS, CPU time, wall time, prompt and output tokens, context length, thread count, hardware, power if available, and quality on the *same tasks*. “Small model” without these quantities is not a testable claim.

## Paths to better quality per resource

### Training, data, and distillation

[Chinchilla](https://arxiv.org/abs/2203.15556) showed that the balance of parameters and training tokens matters under a fixed training-compute budget. It does not imply that arbitrary capability can be packed into arbitrarily few inference bits. [Minitron](https://arxiv.org/abs/2407.14679) pruned and distilled a 15B parent into 8B and 4B models, reporting 2 to 4 times smaller size and less training data than building those derivatives from scratch. This is a plausible method for an efficient candidate, with capability loss to measure.

[Distilling Step-by-Step](https://arxiv.org/abs/2305.02301) reported a 770M student outperforming a few-shot 540B PaLM on a reported NLP benchmark using teacher rationales, across four studied NLP tasks. That is strong evidence for task-specific transfer. It is not evidence of broad equivalence to a newer frontier service. [DeepSeek-R1](https://arxiv.org/abs/2501.12948) also released distilled models from 1.5B through 70B, demonstrating a family of quality and cost tradeoffs rather than a single universally equivalent small model.

Better reasoning post-training can change performance greatly without changing parameter count. The [Phi-4 reasoning report](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/04/phi_4_reasoning.pdf) reports AIME 2025 accuracy rising from 12.9 for its 14B base model to 63.1 for the reasoning variant and 78.0 for reasoning-plus under its evaluation. That result is specific to the benchmark and setup. Longer generated reasoning also consumes tokens, compute, and time. [MobileLLM-R1](https://arxiv.org/abs/2509.24945) reports a 950M model at 15.5 on AIME versus 0.6 and 0.3 for two compared small baselines, further showing that small models can improve substantially within a narrow metric.

**Research implication:** Start with a strong compact pretrained model, then test targeted adaptation on authorized data only after defining a held-out suite. A from-scratch frontier pretraining effort has no credible resource or success estimate from the evidence reviewed here.

### Lower precision and native low-bit training

[GPTQ](https://arxiv.org/abs/2210.17323) showed that 3- and 4-bit weight quantization can preserve much of the tested models' accuracy. The current local files are already Q4_K_M, so repeating ordinary four-bit conversion is unlikely to provide another fourfold reduction. Moving below four bits may save stored bytes but can degrade difficult tasks, and runtime speed depends on the available kernels.

[BitNet b1.58 2B4T](https://arxiv.org/abs/2504.12285) reports a model trained natively with 1.58-bit weights and efficient CPU/GPU inference, with performance comparable to similarly sized open models in its tests. This is evidence that native low-bit design can work better than simply forcing conventional pretrained weights into an extreme format. It does not establish frontier-service parity, and its runtime behavior should be measured on the target device before adopting it.

### Sparse and mixture-of-experts computation

[SparseGPT](https://arxiv.org/abs/2301.00774) reported 50% to 60% unstructured sparsity with limited perplexity loss in its tested older models. Zero weights only reduce actual file size or CPU work when the storage format and compute kernels exploit the sparsity. Sparse indexes themselves cost space, and irregular access can be slower on a CPU.

Mixture-of-experts models activate a subset of experts per token. The [gpt-oss](https://deploymentsafety.openai.com/gpt-oss/architecture) and [Gemma 4](https://ai.google.dev/gemma/docs/core) figures above show the appeal and the constraint: active operation count can fall while total model storage remains large. Expert paging could reduce *resident* RAM, but transfers add latency and storage traffic. The feasibility of such paging on this VM is unmeasured.

### Attention and long context

[Grouped-query attention](https://arxiv.org/abs/2305.13245) reduces key-value heads and therefore cache size in its tested transformer configurations, with a quality tradeoff to check. [KIVI](https://arxiv.org/abs/2402.02750) reported a 2-bit key-value cache and up to 2.6 times lower peak memory in its tested settings. The gain is workload dependent: it matters more when long context or batching makes the cache large relative to weights.

[FlashAttention](https://arxiv.org/abs/2205.14135) improves exact attention's input-output efficiency on GPUs. It should not be quoted as a measured CPU speedup for this repository's VM. A long advertised context window also does not establish useful retrieval or reasoning across that window; the Gemma card's long-context scores illustrate why quality must be tested separately from capacity.

### More work at inference time

[Speculative decoding](https://arxiv.org/abs/2211.17192) can speed generation while preserving the target model's output distribution under its algorithm; the original study reported 2 to 3 times acceleration on a T5-XXL configuration. It does not shrink the target weights, and its draft model adds a resource cost. Google's [Gemma 4 overview](https://ai.google.dev/gemma/docs/core) lists a dedicated draft model, making this an available candidate for latency testing when the target model fits.

[Test-time compute research](https://arxiv.org/abs/2408.03314) found settings in which a smaller model with more inference work beat a model 14 times larger at matched inference FLOPs on problems with some baseline success. This is a quality and compute tradeoff, not a free reduction in CPU or latency. Retrieval, tools, and remote fallback can also improve a *system* on defined tasks, but they must be reported as external dependencies and cannot establish capability of the small local model alone.

## A realistic experiment ladder

The next step should answer a concrete question, such as “Which local model meets an independently specified benign task success rate with a file under X GB, peak RAM under Y GiB, and median CPU time under Z seconds on this hardware?” X, Y, and Z are deliberately unset: the user has not supplied a device budget or target tasks, and choosing them without evidence would make the result arbitrary.

1. **Freeze tasks and success criteria.** Include several benign domains: factual synthesis with source checking, reasoning, harmless code generation with functional tests, instruction following, and long-context retrieval. Add vision only if needed. Define the pass criterion before generating answers. Include hard and ordinary cases and preserve all failures.
2. **Freeze the reference.** Use exact service model identifiers, dates, settings, and the same prompts. Record tool access and the cost of any external service. If access is unavailable, mark reference parity unmeasured instead of substituting a marketing benchmark.
3. **Run compact baselines.** Compare the existing Qwen2.5 0.5B and 1.5B files with one or more current compact candidates, such as Qwen3.5-4B and Gemma 4 E2B/E4B, subject to license and hardware fit. Evaluate original and quantized variants only when the runtime supports the intended format.
4. **Measure jointly.** For every task and configuration, record output, correctness, file bytes, peak RSS, CPU time, wall time, token counts, context length, runtime commit, model hash, and hardware. Use repeated runs for noisy resource metrics. Report timeout and out-of-memory outcomes in the denominator.
5. **Apply one intervention at a time.** Only after baselines, test targeted distillation or fine-tuning, lower-bit weights, cache quantization, or speculative decoding. Keep the evaluation set held out from training and tuning. The training and teacher-output cost belongs in the economic analysis.
6. **Report uncertainty and failures.** Give per-domain scores and confidence intervals, a resource-quality Pareto plot, and representative failure categories. [LiveBench](https://arxiv.org/abs/2406.19314) motivates fresh, objective questions to reduce benchmark contamination, but a project-specific held-out set is still needed.

An initial pilot can use the current CPU VM, but it cannot validate deployment on another device class. The [local resource study](inference-resource-study-2026-11-11.md) already proves that model and prompt choice materially change memory and time on this VM. A dedicated quality suite is the missing evidence. The first defensible decision is whether any compact candidate meets a *defined* quality floor within the actual resource budget. If none does, the measured gap can guide a larger model, different hardware, narrower task, or explicitly counted external service.

## Conclusion

There is no demonstrated ZIP-like way to retain the full capability of a named frontier service while making its local file, RAM, and CPU needs tiny. There are credible and testable gains from better training, distillation, native low-bit models, quantization, sparse computation, cache design, and decoding. Their effects differ by workload and hardware. The research program should measure **quality and resources together**, and should claim parity only for the tasks that pass independent tests.
