# Search and evidence protocol for the Drexel feasibility review

Drafted 26 November 2026 during the source-only research window. This supplements the repository's [observation-level methodology](methodology.md). It describes the actual exploratory search and decision rules; it is **not** a claim that the literature was exhaustively or systematically searched. The [dated log](research-log-2026-11-26.md) records the questions pursued and the [source registry](../data/sources.json) records cited material.

## Review questions

1. Can a continuing program apply changed executable code without losing its required state and service? Which update mechanisms and boundaries are documented?
2. Which published malware cases show a model output linked to a specific payload-code revision, rather than model-selected actions, new scripts, new builds, configuration changes, or model-weight updates?
3. Does any one report or independently linked set of records show **two accepted changes in the same identified process**, with remote-control function checked after each? This is the strict Project Drexel research subclaim, not an observation assumed by the review.
4. What do original studies establish about cumulative revision reliability, model placement, resource costs, and endpoint visibility? Which numerical results cannot be transferred to the Drexel chain?

## Search and selection used in this window

Searches combined terms for `LLM`, `model`, `AI`, `self-update`, `self-modifying`, `RAT`, `implant`, `payload`, `runtime`, `in-memory`, and `C2`, with narrower searches for named families and report authors. Candidate reports were followed to the investigating team's original publication, technical note, code repository, or paper. Technical feasibility claims were checked against official runtime, operating-system, or telemetry documentation and original dynamic-software-update studies. Secondary summaries were used as leads or to identify a source conflict, not as an independent execution trace. The 26 November source pass specifically rechecked PROMPTFLUX, HONESTCUE, C2Agent, KUKURAT, Emotet, ArcticRAT, GREYVIBE, SCMBANKER, and the Unit 42 Latin America campaigns, along with controlled benign revision and dynamic-update work. Later targeted searches screened live-reload agent repositories and the first-party Amazon Cairn and Gambit retailer reports against the same process/version rule. A same-publisher short overview was not assumed to override its earlier detailed sample analysis.

Cases enter the claim-level [master matrix](master-feasibility-evidence.md) when they provide at least one potentially relevant component: a resident model call, generated and executed code, live module loading, an upgrade path, changing builds, or remote-access checks. A case can be included while failing the full hypothesis. Bare “AI-powered” labels, headlines, model downloads without inference, unrelated AI-themed lures, and version names without code evidence cannot fill a missing causal or process link. This review does not treat absence of a published trace as evidence that private telemetry contains none.

## Claim-level extraction

For each candidate, record the **unit** being counted: prompt, model response, candidate artifact, distinct code revision, attempted application, accepted live version, working remote-control task, or incident. Keep the denominator and experiment setting attached to every rate. Record model placement separately from code placement. A report can support one stage of the chain without supporting the next.

The four necessary links for the strict claim are: stable instance identity; a particular model response mapped to each changed code artifact; proof that each new version became active; and an independent remote-control result after each of two changes. Service reachability after a restart is a different outcome and should be labeled as such. For a case with only a reported update feature, classify the feature as a **mechanism**, not an observed use. For a case with AI-style comments, classify authorship as the investigator's **inference** unless a model interaction is captured.

Treat an attacker-side or agent-side transcript as a provenance lead, then cross-check its claimed commands and outputs against separately collected artifacts or defender records when available. [METR and Redwood Research](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/) documented small-scale tool-call spoofing in part of their evaluated transcript set and noted incomplete capture in their independent incident review. This does not make all transcripts unreliable; it makes record integrity, collection scope, and corroboration part of the evidence grade. A model conversation alone cannot prove that a proposed code version became active.

## Current limitations and next search

This is an evolving narrative review with heterogeneous public sources, uneven disclosure, and no standardized incident telemetry. It cannot estimate the prevalence of AI-revising RATs, the probability that two revisions succeed, or an endpoint alert rate. The source registry includes records from earlier project phases; its size is not a count of independently observed Drexel-like cases. No model or malware was run in this research window.

The highest-value next source is a primary incident timeline or controlled study publishing a joined model request/response, accepted artifact versions, process lineage, and independent command results for two serial changes. A later report that only adds more samples, variants, or named AI products would not resolve that evidentiary gap.
