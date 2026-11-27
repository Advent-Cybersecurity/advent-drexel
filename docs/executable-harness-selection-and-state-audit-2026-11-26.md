# Executable harness selection and state survival

Advent Cybersecurity source audit, 26 November 2026. This is a review of author-reported benign studies. No model or agent was run. The relevant Drexel question is whether evidence for executable agent-code improvement also establishes serial adoption and function in one continuing remote-access process.

## Learned executable patching

[Harness-R1 v1](https://arxiv.org/html/2608.02276v1) trains a separate 9B harness engineer to emit executable Python patches from batches of target-agent failures. The frozen target is rerun on the same tasks after a patch. Across WebShop, ALFWorld, and DBBench, the authors report an equal-weight success increase from 44.3% to 53.6%. A sparse-failure protocol generated one benchmark-specific patch from ten observed failures per benchmark/seed and tested it on the remaining 1,270 tasks: +8.9 ± 1.5 percentage points over three evidence seeds. Those are task outcomes after fresh reruns, not serial revisions within one running task instance. The paper's inspected off-the-shelf editor example shows why valid patches alone are weak evidence: among 39 valid patches, 21 lowered same-batch success, 12 raised it, and six left it unchanged. These 39 are from that example, not the learned editor's overall failure rate. The training and evaluation resources include H800 GPUs; this does not measure a small CPU-resident controller.

[AIDE² v1](https://arxiv.org/html/2609.26457) gives a stronger repeated-source-lineage comparison. In one eight-day, 100-node outer trajectory, 99 proposed rewrites yielded seven accepted harness-code changes at steps 2, 6, 28, 39, 47, 63, and 85; its selection grade rose from 0.703 to 0.778. Two additional full runs accepted two and four rewrites. Candidate agents were evaluated on separate fresh tasks under a fixed budget. Four external benchmark families checked the selected versions, while the authors explicitly identify grade noise and false acceptance as risks. The outer model was Claude Opus 4.7 and the main inner evaluator Gemini 3 Flash. This shows that repeated model-proposed executable-harness changes can be selected and evaluated, but not that they are activated in one resident process or preserve a remote-control task after each.

Neither paper provides a Drexel success probability. Their units are benchmark patches, proposed/accepted harness versions, and independent task reruns, not continuing remote-access instances. Their outcome measures should remain separate from process identity, code adoption, and command/result evidence.

## Restart is not just a state-storage question

[Mastouri et al.'s container-deployment study](https://arxiv.org/html/2610.34620v1) analyzed 433 selected public LangGraph deployments. Among the 265 systems for which durable state was required, 99 (37.4%) failed the process-restart state contract and 110 (41.5%) failed the container-replacement contract. Of 61 applicable background-work systems, 54 shipped no mechanism to resume an interrupted run. In selected runtime checks, 14 of 16 predicted violations and all seven predicted holds matched observed behavior. These results concern that study population, and its repository-derived resumption classification is not a measured Drexel failure rate.

The transferable methodological point is that **stored state, resumed work, and retained function are distinct outcomes**. A system can keep a conversation or task file through a restart yet never resume the interrupted operation. A paper claiming a continuing resident program must identify both the execution boundary and what happened to in-progress work; a stored transcript or reconnected service alone is insufficient.

## Implication for the paper

Report separately: proposals, byte-distinct executable patches, accepted patches, actual code activation, task execution on each active version, state preservation, and independently verified functional outcomes. When evaluating a second change, retain the first version's outcome and any regression or rollback; do not infer serial success by multiplying unrelated per-task benchmark rates.
