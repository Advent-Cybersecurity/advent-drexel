# COGENT endpoint claims: an abstract-level audit

26 November 2026. Source review for Advent Cybersecurity; no model, sample, or endpoint test was run.

## Sources and access limit

- [Kanso et al., *COGENT: A Framework for Studying LLM-Guided Adaptive Evasion in Endpoint Security*](https://ieeexplore.ieee.org/abstract/document/11760091), IEEE CSR 2026, DOI 10.1109/CSR69374.2026.11760091. The public IEEE abstract was available; its full methods and result tables were not obtained in this review.
- [Kanso, *Generative Steganography for Covert Command-and-Control Communication: Modeling and Detectability Study*](https://scholarworks.aub.edu.lb/items/d3271246-23d8-4417-b5b0-b42c06e02131), American University of Beirut master's thesis, deposited September 2026. Its repository abstract was available, but the thesis PDF was marked **restricted / request a copy** when checked on 26 November. The thesis may cover a later or different COGENT configuration; its 45-run matrix must not be assumed to be the conference paper's mutation-cycle experiment.

## What the available primary text reports

The conference abstract says COGENT fingerprints the endpoint at runtime, uses GPT-4o-mini to choose techniques from a curated library and generate semantically equivalent code variants, and evaluates execution duration against baseline polymorphic samples over multiple automated mutation cycles on isolated Windows VMs. The abstract does not give the exact cycle denominator, identities of products, per-product outcomes, code-version lineage, process continuity, or independent command/result checks after each variant. Its phrase “multiple automated mutation cycles” therefore establishes an author-reported *search or adaptation sequence*, not by itself two active revisions in one continuing process.

The thesis abstract describes COGENT with an image-based command-and-control subsystem called Typhon. It says a model ranks one primary and three fallback techniques. It reports 45 thirty-minute runs across 15 endpoint products, with Suricata, Snort, or OSSEC active in each run; all 45 bidirectional workflows completed and the tested controls issued no relevant alert or block in that matrix. A separate detailed ARGUS run detected COGENT and issued a central alert. These are the author's abstract-level claims. The public text does not specify whether a fallback was exercised in a given run, whether executable code was revised *after launch*, whether the same process survived such a revision, which command/result criterion defined a completed workflow, or how alerts were scoped and collected. The absence of a relevant alert in that bounded matrix is not a universal undetected rate. The separate ARGUS finding also prevents a blanket claim that COGENT was undetectable.

## Four-link Drexel assessment

| Required link | Status from accessible text |
| --- | --- |
| One continuing remote-access process across changes | Unshown; per-run process identity and restart history are unavailable. |
| Model-caused executable payload-code change | Described for generated conference variants; timing and active adoption are unshown. The thesis abstract describes model-ranked techniques, which may be a different intervention. |
| Two distinct revisions active in that process | Unshown; mutation cycles are not documented as in-process activations. |
| Independent remote-control result after each active revision | Unshown. The thesis reports bidirectional workflows per run, not version-bound outcomes. |

COGENT is one of the closest public endpoint claims found in this review, especially because its author explicitly combines model-guided code variants with controlled endpoint evaluation. The confidence ceiling is **abstract-level** until the full conference paper or thesis methods can be inspected. A future literature update should request/access those texts and audit the process lineage, version timestamps, functional oracle, product configuration, alert source, and denominator before extracting a Drexel rate.
