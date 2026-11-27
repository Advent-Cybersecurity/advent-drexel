# Two revisions in a controlled agent harness: what the result measures

26 November 2026. Source-only audit of [*Can LLMs Improve Their Own Harness?*, version 2](https://arxiv.org/html/2610.30499). No model or program from the study was run here. This paper is unusually relevant because it follows **two cumulative, model-authored code revisions** rather than counting isolated first attempts. Its task and process architecture remain distinct from Drexel.

## Design and evidence unit

The study uses nine model-and-effort conditions, three independent harness lineages per condition, for **27 lineages**. Each begins with a model-built Python task harness, then receives two opportunities to revise that harness. The *coding bootstrap* stays fixed. Each proposed stage must pass a limited smoke qualification: execute and interact with two development games, without a minimum performance score. A failed candidate can be repaired for up to ten cycles. The resulting three snapshots per lineage are frozen and evaluated on five development games and twenty feedback-withheld games. All 27 lineages completed both revisions, giving **54 transitions and 81 frozen snapshots**. The authors replayed game actions against local and official services to check recorded scoring. [Protocol and results](https://arxiv.org/html/2610.30499).

All 54 scored transitions changed source: each added or removed at least 84 lines, with a median of 449. This establishes substantive *artifact* changes in the experiment, but each frozen snapshot is evaluated as its own task execution. The paper does not claim that one identified, continuously running process adopted both versions while preserving state or network access. A new snapshot's qualification means it starts and interacts, not that it preserves all prior function. [Source audit](https://arxiv.org/html/2610.30499).

| Reported result | Correct denominator and interpretation |
| --- | --- |
| Mean development-game change from initial to second revision: **+8.42 RHAE points**. | Paired comparison across 27 lineages on the same five development games used to guide revision. |
| Mean held-out change: **+2.80 points**, 95% lineage-bootstrap interval **−1.44 to +7.35**. | Same 27 lineages on twenty games withheld from adaptation. The interval includes no mean benefit. |
| Held-out strict signs: **15 gains, 12 losses**. At a five-point descriptive threshold: **9 gains, 3 losses, 15 smaller changes**. | Observed suite-score differences, not probabilities that a future code change preserves a resident service. Each snapshot was principally evaluated once; gameplay itself varies. |
| A development-score selector gives a **post hoc** mean held-out gain of **+4.53 points** and retains the initial version in **9** lineages. | A diagnostic selection rule specified after the authors saw held-out outcomes. It separates generating a changed artifact from choosing to deploy it; it is not a prospectively validated controller. |

The authors estimate at least **$18,129.27** for their full experimental program under a fixed price schedule, with most spent on fresh game evaluations. That amount describes this frontier-model, interactive-game protocol and is **not** a Drexel implementation cost. They also report one frozen final harness's twenty-game suite having a 3.99-point sample standard deviation over ten repeat evaluations; most snapshots were not repeated. The 27 lineages have limited power for small mean changes, and the held-out games were public. [Results and limitations](https://arxiv.org/html/2610.30499).

## Relevance to the Drexel feasibility question

The study strongly supports a narrower statement: frontier models, through a fixed coding environment and controller-run qualification, can create **two successive changed code snapshots** in a benign agent workflow. It also shows why changed code, smoke qualification, selected deployment, and preserved held-out behavior are separate outcomes. Its mean development gain is larger than its mean held-out gain, and several lineages regress on withheld games after two revisions.

It supplies neither the process-identity record nor the after-each remote-control result needed for the expanded Drexel hypothesis. Its 15/27 positive held-out endpoints, 9/27 five-point gains, and +2.80 mean cannot be used as a success probability for an endpoint implant. The paper's useful methodological contribution for a later **benign** Drexel test is to preserve all version snapshots, report the full chain from proposal to activation to independent function, and allow a measured decision to retain the incumbent when a candidate fails to justify replacement.
