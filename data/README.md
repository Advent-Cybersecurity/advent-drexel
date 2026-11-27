# Data and experiment records

This directory holds source registries, frozen task manifests, raw results, and logs cited by [the research guide](../docs/README.md). File names usually identify the experiment and collection date. A raw record is not a validated study result by itself; read the linked note for admission checks and interpretation.

## Evidence registries

- [sources.json](sources.json): original reports, papers, and source metadata.
- [observations.json](observations.json): dated case observations and evidence labels.
- [closest-case-claim-ledger-2026-11-26.json](closest-case-claim-ledger-2026-11-26.json): 31 selected component cases coded against the four links of the expanded Drexel hypothesis as of 26 November. The file defines its status codes; `not_shown` means public evidence is insufficient, not that an event was impossible or absent. Cases are selected for relevance and are not a prevalence denominator.
- [selected-case-extraction-2026-11-27.json](selected-case-extraction-2026-11-27.json): nine purposively selected cases re-extracted on eight uniform fields with first-party source locators and explicit public-record unknowns. Read the [bounded case update](../docs/case-evidence-update-2026-11-27.md) for selection and search limits. This does not supersede the other 22 cases in the prior ledger.
- [live-update-case-extraction-2026-11-27.json](live-update-case-extraction-2026-11-27.json): four further cases from that 31-case ledger, re-extracted on the same eight fields. Read the [accepted-version evidence note](../docs/live-update-evidence-chain-2026-11-27.md) for the source boundaries. Eleven of the 31 prior cases now have eight-field records; 18 do not. The two newly added cases in the nine-case pilot are outside the prior ledger.

## Model-efficiency records

| Family | Records and interpretation |
| --- | --- |
| Storage and local inference | `lossless-compression-*`, `foldz-storage-*`, and `inference-resource-study-*` contain storage or CPU-only measurements. See the [lossless study](../docs/lossless-model-compression-study-2026-11-11.md) and [inference study](../docs/inference-resource-study-2026-11-11.md). |
| Same-base quantization | `same-base-*` and `output-head-*` contain tensor maps, rules, and paired pilot runs. See the [same-base pilot](../docs/same-base-quantization-pilot-2026-11-12.md) and [output-head pilot](../docs/output-head-cpu-pilot-2026-11-12.md). |
| CPU runtime | `frontier-cpu-*` contains installed-file censuses, served-task runs, warm and cold memory trials, and rejected attempts. The [second CPU audit](../docs/frontier-cpu-runtime-research-2026-11-13-round2.md) specifies which trials were admitted. |
| Public quality development | `generated-quality-*`, `frontier-quality-*`, and `gsm8k-pair-*` contain manifests, public calibration outputs, scores, and server logs. These are development diagnostics, described in the [quality audit](../docs/frontier-quality-research-2026-11-13.md). |

## Same-source Qwen3 study, November 21

The [artifact provenance](qwen3-same-source-artifact-provenance-2026-11-21.json) records source revision, local hashes, model bytes, and the pinned runtime. The quantized model files are held outside this repository. [The public 32-case development summary](qwen3-same-source-structural-dev-summary-2026-11-21.json) covers the Q4_K_M reference only. [The held-out 240-case manifest](qwen3-same-source-structural-eval-2026-11-21.json) and [its key audit](qwen3-same-source-structural-eval-key-audit-2026-11-21.json) were frozen before held-out execution.

The [reference evaluation record](qwen3-same-source-structural-eval-reference-interrupted-2026-11-21.json) was interrupted after 73 of 240 requests. Its [server log](qwen3-same-source-structural-eval-reference-interrupted-2026-11-21.log) is retained for audit. There is no candidate held-out record, completed paired score, or final same-source resource comparison. Do not use the partial run as an estimate of preserved quality.

## File conventions

- `.json` is structured metadata or a result record; `.jsonl` is one result per line.
- `.log` preserves command or server output used to audit a run. Some logs describe rejected or incomplete trials.
- `.txt` contains frozen tensor or quantization rules where cited by a study.
- Paths in historical records identify the original host's cache and are not portable download links. Hashes and source revisions are the intended provenance checks.
