# Drexel feasibility research

This repository assesses public evidence for model-driven changes in deployed software and studies the resource cost of local language models. It keeps source claims, local measurements, and untested hypotheses separate. The repository contains research notes, benign evaluation code, and data records, with no malware samples or executable payloads.

## Read the research

1. [Project Drexel LaTeX paper and Zenodo upload bundle](paper/README.md) present Jashid Sany's publication-reviewed version 0.4 preprint and its archived evidence trail.
2. [Master feasibility evidence](docs/master-feasibility-evidence.md) gives the central findings and evidence limits.
3. [26 November source-review decision brief](docs/source-review-decision-brief-2026-11-26.md) summarizes the eight-hour source-only review and the remaining evidentiary gap.
4. [27 November source-only research update](docs/source-only-research-update-2026-11-27.md) integrates the latest case, platform, and observation-validity reviews for a future paper version.
5. [Research guide](docs/README.md) indexes every detailed note by topic.
6. [Data guide](data/README.md) explains source registries, raw runs, and incomplete trials.
7. [Script guide](scripts/README.md) maps the reproducibility tools to their studies.

Version 0.4 is published on [Zenodo](https://doi.org/10.5281/zenodo.24591891) as a preprint with its PDF and research archive (DOI: `10.5281/zenodo.24591891`).


## Current model-efficiency finding

As of the completed November 13 evidence audit, no reviewed source or local candidate had jointly shown smaller complete deployable bytes, lower peak CPU RAM, fewer CPU-seconds for a complete request, and preserved quality on sealed benign dependent-step tasks against a same-source Q4_K_M reference. The local Qwen3-4B Q4_K_S model file saved 113,971,200 bytes. In the tested warm no-repack served tasks it used less peak process RAM but more whole-server CPU time than Q4_K_M. Changing the runtime repacking policy reversed the RAM result. See the [paired CPU audit](docs/master-feasibility-evidence.md#13-november-cpu-architecture-and-quality-evidence).

On November 21, a later same-source Qwen3 pair was prepared and a 240-case held-out manifest was frozen. The Q4_K_M reference run stopped after 73 requests when the study was paused. The Q4_K_S candidate was not run. Those partial records are [preserved for audit](data/README.md#same-source-qwen3-study-november-21), and no held-out quality conclusion follows.

## Evidence question

Project Drexel asks whether a custom local language model could support adaptive code and behavior across specified operating environments while retaining function under named defender configurations. A stricter subquestion asks whether one continuing process can apply two model-caused executable revisions with an independent function check after each. The [master evidence assessment](docs/master-feasibility-evidence.md) distinguishes reported components from a documented end-to-end sequence. Its conclusion is a limit of available public evidence, not proof that the behavior is impossible.

The [25 November 2026 source update](docs/feasibility-source-update-2026-11-25.md) adds recent field observations of agentic intrusions and new evidence about reliability across successive code changes. It does not change the end-to-end verdict. No new model test was run for that update.

## Scope and provenance

The [methodology](docs/methodology.md) defines evidence labels and inclusion rules. [Sources](data/sources.json) and [observations](data/observations.json) are machine-readable. Dated reports preserve the methods, denominators, conflicts, and negative results behind the summaries. Large model binaries and runtime caches are not committed; local artifact hashes and pinned upstream revisions appear in the raw provenance records.
