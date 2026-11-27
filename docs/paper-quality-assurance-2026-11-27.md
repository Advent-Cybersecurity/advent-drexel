# Project Drexel paper: version 0.2 quality assurance and version 0.3 corrections

Advent Cybersecurity, 27 November 2026. This review examined the [version 0.2 source](../paper/drexel-feasibility-v0.2.tex), its PDF, the source registry, the 31-case ledger, and the Zenodo bundle. It checked selected quantitative claims against original studies, reviewed the inference and study design, rebuilt the LaTeX, inspected rendered pages, and checked archive integrity and local links. It was a targeted quality review, not an exhaustive verification of the 512-source registry. No model, agent, malware, or payload was run.

## Material findings and corrections

| Finding in version 0.2 | Correction in version 0.3 |
| --- | --- |
| The archive claimed to preserve its evidence trail, but its selected Markdown files had 56 broken relative-link occurrences to 44 in-repository targets. The cited [CPU pilot](inference-resource-study-2026-11-11.md) and its raw records were absent. | The packager now includes the complete current `docs`, `data`, and `scripts` trees, plus the paper, repository guide, and a SHA-256 manifest. Internal archive links are checked after packing. |
| The method stated that unit, placement, activation, function, and source type were recorded for every selected case, while the [archived ledger](../data/closest-case-claim-ledger-2026-11-26.json) contains source IDs, setting, four link statuses, and a note. | The method now describes the actual archived fields and identifies the lack of uniform structured extraction as a limitation. The 31 cases remain a relevance-selected audit of the strict serial-revision subclaim, not an RQ1/RQ2/RQ4 sampling frame. |
| RQ1's wording could credit a fixed program that succeeds across environments as adaptive. | The question and proposed study now require an observation-to-model-decision-to-behavior record and unchanged/fixed-rule controls under a changed benign condition. Coverage and adaptation are reported separately. |
| The strict RQ3 code-change rule did not distinguish model-authored code from a model's choice of an existing module. | The rule now requires model-authored or materially edited executable code with an inspectable transformation and acceptance path. Selecting existing behavior remains eligible for behavioral-adaptation analysis but not this code-authorship subclaim. |
| The advertised full-chain rate, $N_2/N_0$, conditioned on a functioning baseline and omitted failed launches. | The paper now names $N_L$ as all eligible launch attempts and reports conditional serial-revision success $N_2/N_0$ separately from overall launch-to-$S_2$ feasibility $N_2/N_L$. |

## Source and wording corrections

- The [Radovič paper](https://arxiv.org/html/2610.14209v1) lists Boris Radovič, Marco Canini, and Veljko Pejović. The [EDR paper](https://arxiv.org/html/2606.08168v2) lists Kerri Prinos and Lilianne Brush. Version 0.3 corrects both reference entries.
- The [Google report](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) now has its full published title in the bibliography.
- ESET's [PromptLock report](https://www.eset.com/blog/en/research/first-known-ai-powered-ransomware-uncovered-eset-research/) characterized the academic prototype as closely resembling the samples. The paper now states the resemblance and ESET's proof-of-concept assessment without asserting proven sample provenance.
- The [Hortea study](https://arxiv.org/html/2605.03619v3) result is clarified as 100 samples in each of stages 3 and 4 under both prompting modes. The local pilot wording specifies a 128-token prompt and 64 generated tokens per process run.
- Printed bibliography entries now display complete URLs rather than only linked domain names.

The checked numerical claims for LLMalMorph, Hortea, Raz, Normann, Avllazagaj, Kitsune, and the Advent CPU pilot otherwise matched the cited primary sources at their stated units. This is not a claim that every bibliographic item or all 512 registry records were independently reverified in this pass.

## Artifact validation after correction

Tectonic compiled the revised manuscript to a 14-page PDF with the expected title and author metadata. All 31 bibliography keys are cited and resolved, and the log has no citation, reference, overfull-box, or fatal LaTeX warnings. All 14 pages were rendered and visually inspected for clipping, table overflow, and legibility. The new ZIP holds 239 payload files plus its manifest; CRC and SHA-256 checks pass for every file. All 728 local Markdown links inside the ZIP resolve to archived targets. The ZIP also contains the CPU pilot note and both raw JSON records. The extracted LaTeX source rebuilt to a 14-page PDF. The source registry has 512 unique IDs and URLs, and all 31 selected cases refer to registered source IDs. These checks verify the artifact and internal consistency; they do not validate every claim in the source registry.

## Publication limits after correction

Version 0.3 remains a preliminary narrative preprint, not a completed PhD dissertation, systematic review, or empirical Drexel demonstration. Its 31 selected cases do not estimate real-world prevalence or feasibility rates. RQ1, RQ2, and RQ4 still need separately specified search/evidence matrices before strong literature-wide claims. A later empirical protocol must fix quantitative thresholds, sample-size logic, sensor windows, and uncertainty rules before collecting results. The PDF is readable and visually inspected but is not a tagged accessibility PDF. No Zenodo DOI or license has been assigned by this project.
