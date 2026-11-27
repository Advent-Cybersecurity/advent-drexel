# Why component success does not establish full-sequence success

**Reviewed:** 2026-11-11. **Status:** Research assessment. No autonomous agent or offensive workflow was built or tested.

## The problem

[Anthropic's October 2026 evaluation](https://www.anthropic.com/research/self-replicating-ai) reports that models with 30 billion parameters or fewer completed many individual tasks in its controlled study but made mistakes when combining them. That is a distinct limitation from a model's ability to answer a single prompt. A sequence can fail because an early error changes the state on which later steps depend, and the later steps can appear locally reasonable while pursuing the wrong state.

This pattern also appears outside cyber research. The [Traverse study](https://arxiv.org/abs/2609.17930) examined 2,518 agent trajectories across software engineering, computer use, and science. Its authors report that agents often failed to notice their first mistake or recover from it. The [HORIZON study](https://arxiv.org/abs/2604.11978) reports performance degradation over longer, interdependent task sequences across four domains. These are research findings, not measured failure rates for this repository's proposed system.

For intuition only, if ten required steps each had an independent 90% chance of success, the chance of all ten succeeding would be about 35%. Real steps are dependent, so this calculation is not an estimate of any model's actual performance. It shows why high component accuracy can coexist with weak whole-task reliability.

## Research directions for benign software agents

| Direction | What it addresses | Cost or limit |
| --- | --- | --- |
| Narrow the task and define observable success | Reduces ambiguity about whether the complete task worked | A result on a narrow task does not transfer automatically to new environments |
| Use independent functional checks | Finds invalid changes and regressions that a model's own judgment might miss | Tests can be incomplete or wrong; checking adds execution time and resources |
| Record intermediate state and failures | Makes the first error and recovery visible in the evidence | More storage and instrumentation are needed |
| Stop or revert when checks fail | Limits error propagation through later steps | May lower the fraction of tasks completed and increase attempts |
| Compare complete trajectories on held-out tasks | Measures the combined behavior rather than isolated answers | Long runs cost more and need reliable ground truth |

These are broad evaluation and control principles. They do not establish that a small model can carry out a long task reliably. Better checking may improve reliability at the price of more CPU time, memory, or latency. That tradeoff directly affects the compact local-model goal.

## What would count as evidence here

The next safe experiment is the [benign revision study](feasibility-constraints-and-study-plan.md): a non-networked application with predeclared functional tests, several dependent revisions, and all attempts retained. Report isolated-step success, complete-sequence success, the first failure point, recovery, regressions, and total model plus checking cost. Compare those results across pinned model versions and the same held-out tasks. A single successful demonstration or a benchmark score without validated ground truth would not settle the question. [OpenAI's audit of SWE-bench Verified](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) illustrates why the test set itself needs scrutiny.

**Current judgment:** The evidence supports improving verification and measuring full sequences, but it does not show a general fix for small-model composition errors. Any proposed improvement must be judged against the added resource cost and an independent end-to-end success measure. This assessment does not design or validate malware creation, evasion, or autonomous propagation.
