# Local code-model file size, solved tasks, and energy

26 November 2026. Source-only audit of Aditi Patodiya, [*Choosing Quantized Code LLMs by File Size and Energy per Solved Task*, arXiv v1](https://arxiv.org/html/2611.17605) (13 November 2026). This is an author-reported experiment; its released per-task artifact was not independently rerun here. No model was loaded or tested for this audit.

## What was measured

The study used 24 shipped Qwen2.5-Coder-Instruct GGUF files across 0.5B, 1.5B, 3B, and 7B sizes. Ollama 0.32.6 ran llama.cpp through **Metal acceleration** on a fanless, 16 GB MacBook Air M2. Each file received one greedy answer for each of 542 standalone EvalPlus Python tasks (164 HumanEval+, 378 MBPP+), with a 2,048-token context and 768-token output cap. A solution counted only when it passed base and plus tests. The main grid used one session per benchmark and file, in a fixed file order. Macmon sampled CPU, GPU, and memory rail power, with marginal joules per solved task computed from task windows. Thus this is a local-device result, **not a CPU-only result** or a measure of endpoint-protection behavior (study §§ III-A–E).

| File | Listed size | Solved / 542 | Rail joules per solved task |
| --- | ---: | ---: | ---: |
| 1.5B q4_K_M | 0.99 GB | 316 | 39.3 |
| 3B q4_K_M | 1.90 GB | 366 | 69.4 |
| 7B q2_K | 3.00 GB | 363 | 141.2 |

At the key comparison, the 3B file solved three more tasks than the heavily quantized 7B file. The paired 90% interval for the 3B-minus-7B pass-rate difference was **−2.40 to +3.51 percentage points**. The authors call 3B non-inferior using a **post hoc three-point margin**; they do **not** establish equivalence. The 7B/3B rail-energy-per-solve ratio was 2.03 in the main grid (95% within-session task-bootstrap interval 1.91–2.17); whole-system accounting gave 1.66–1.81 depending on idle treatment. Five alternating HumanEval+ session pairs yielded 1.925 (95% between-session interval 1.718–2.157). The pair was chosen after the main grid, the repeated task set was only HumanEval+, and all ten valid repeat blocks were flagged for conditions that included thermal pressure (Tables I–III; §§ III-F, IV-C, VI).

The 3B q3_K_M file is a useful warning against selecting from the nominal quantization tag or file size alone: it solved **7/542** tasks despite its 1.60 GB listed size. The paper attributes this failure to its plain uncalibrated quantization and reports partial improvement with an importance matrix. The file-size budget is the listed download size, **not complete loaded memory or runtime-buffer cost** (§§ III-A, IV-A, V).

## Feasibility interpretation

This paper supports a narrow but useful proposition: on one laptop and one model family, file size, effective quantization, solved-task rate, latency, and energy should be evaluated jointly. The repeated anchor strengthens one energy comparison; the fixed-order single-session grid limits other cross-file energy rankings. The equivalence margin and budget choices were selected after results were seen. A model's apparent savings per output token can also differ from savings per **working answer**.

It does **not** measure the quality of a dependent second edit, two active versions in one process, a retained remote-control session, or an endpoint alert. The EvalPlus tasks start independently and the host used a GPU. No Drexel success rate, CPU-only deployment budget, or detection probability can be inferred from these counts. A prospective benign analogue would need complete deployed bytes, peak memory, latency and energy for the whole two-revision sequence, and a joint functional-success denominator that includes failed candidates and regressions.
