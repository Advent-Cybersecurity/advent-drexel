# Methodology

## Research question

What public evidence shows how APT operators change malware or its delivery over time, and how does that compare with reported AI-assisted or runtime AI behavior?

## Unit of analysis

Each row in `data/observations.json` is one *reported observation*, not necessarily one binary, version, incident, or independent confirmation. A single report can support more than one row when it describes distinct changes. The dataset is selective and is not a census of APT activity.

`observed_start` and `observed_end` mark the interval described by the source. They are not publication dates. For `observed_sample` records, the interval can be a documented sample upload or first-seen date; it is not a confirmed infection date. A month- or half-year-level report is recorded as an interval, not assigned an invented exact day. `month_range` brackets separately reported sightings or variant activity to month precision; it does not assert uninterrupted activity between them. Each source's `published` field records an exact report date when known; `null` means no exact first-publication date was established. For a pinned repository-code source, the field may instead record the cited commit's date: that dates the inspected snapshot, **not** the file's first appearance or a test run. `publication_month` may preserve a month-level date supplied by the source. A source may separately have a `last_updated` date. A sample timestamp is not treated as proof of compilation time or authorship.

## Classification

| Field | Meaning |
| --- | --- |
| `change_class` | `delivery_revision`, `component_portfolio`, `target_specific_build`, `sample_variation`, `development_ai_assistance`, `runtime_ai_generation`, `runtime_command_generation`, `runtime_action_selection`, `runtime_ai_triage`, or `attempted_runtime_mutation`. The runtime classes distinguish generated commands, model-guided actions, and analysis of collected data. |
| `control_point` | Where the change occurred: `operator_or_build`, `delivery_service`, `on_host`, or `unknown`. |
| `ai_role` | `none_reported`, `development_assistant`, or `runtime_model_call`. This reports evidence, not a claim that AI was absent elsewhere. |
| `attribution` | The source's wording or confidence. `unattributed` means the source did not link the sample to a tracked actor. |
| `status` | `observed_operation`, `observed_sample`, or `researcher_assessment`. A sample alone does not establish successful deployment. |
| `source_locator` | The report section or paragraph that supports the observation; it is more stable than a scraped line number. |
| `evidence_basis` | What investigators observed or analyzed, such as incident artifacts, samples, or model-service activity. |
| `corroboration` | Other investigation reports and their relationship to the primary observation. Omitted for rows not yet cross-checked. |

`corroboration.relationship` is `direct` when a second investigation independently analyzes the same specific artifact or event; `partial` when it supports some, but not all, of the observation; `contextual` when it describes related activity without verifying the specific claim; and `divergent_assessment` when the sources interpret a material point differently. The accompanying note names the supported and unsupported parts. A report that merely repeats an earlier report is not independent corroboration.

## Evidence rules

1. Prefer incident responders, product security teams, and the researchers who examined the samples. Link each claim to its specific report.
2. Keep source claims separate from our interpretation. `observation` paraphrases the report; `interpretation` states what the observation may mean for the research question.
3. Preserve stated uncertainty and attribution qualifiers. Similar code or behavior alone does not prove a shared developer.
4. Do not infer runtime adaptation from multiple samples, or infer AI from obfuscation, modularity, or rapid release cadence.
5. Treat continuous adaptation as a Project Drexel research hypothesis, not an observed property. Evidence would need to establish that a running program made and applied changes repeatedly, that resulting variants remained functional, and whether this occurred in operations or only in a controlled study. See the [feasibility assessment](drexel-feasibility-assessment.md).

## Limits

Public reports reflect uneven visibility and different naming systems. The researchers generally observe artifacts and incidents, not the group's internal development process. Findings therefore describe observed engineering choices and clearly labeled inferences. No malware samples are downloaded or executed for this study.

The [2026 evidence update](2026-evidence-update.md) also includes a controlled research preprint and a vendor telemetry survey. Those are kept in a separate note because their experiment dates or unit of analysis do not match the incident-observation rows in `data/observations.json`. A research demonstration, an analyzed binary, and an observed intrusion are not interchangeable evidence of operational malware capability.
