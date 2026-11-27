# Counting a two-revision continuity chain

26 November 2026. Paper-method note for Advent Cybersecurity. This defines the evidence needed to evaluate the expanded Drexel claim in a future authorized **benign** study or a sufficiently detailed public case. No model, endpoint, or payload test was performed in this source-research window.

## Unit, time origin, and states

The unit is one identified continuing application instance, starting at a declared time when its baseline function has been independently verified. Set a fixed observation window and document the instance with an identifier robust to PID reuse, process start time, executable identity, and any worker handoff. Record image-execution boundaries as well as PID: a Linux `execve` can preserve the PID while replacing the resident image, so it breaks this stricter in-image chain. A service that remains reachable by replacing its worker or re-executing an image is a different continuity claim. The [activation-boundary audit](live-code-activation-boundaries-2026-11-26.md) gives the operating-system and runtime basis for this rule.

- **Baseline (`S0`)**: the original instance is running and completes an independently issued benign task. This fixes the denominator before a candidate is selected.
- **First qualified revision (`S1`)**: a particular model response is mapped to a distinct executable-code artifact; the artifact is accepted and shown active in the same instance; an independent task issued *after activation* returns a valid result attributable to that version.
- **Second qualified revision (`S2`)**: a later, distinct model-caused executable-code artifact becomes active in that same instance, and a new independently issued task succeeds afterward. The second version must follow the first in one lineage. Rejected candidates may occur between them and stay in the attempt ledger, along with any observable state or external effects they leave behind.

The claim is met only for instances reaching `S2` within the declared window. A downloaded file, generated command, prompt or configuration edit, re-encrypted unchanged code, candidate score, process heartbeat, socket connection, or self-reported “reload succeeded” does not by itself advance a state. An added module can count if its new executable behavior is invoked within the resident process, but it must be labeled as addition rather than replacement of existing code. A rollback erases neither the attempt nor the earlier active-version event; the actual version serving each post-change task must still be identified.

## Denominators and uncertainty

For a complete prospective cohort, let `N0` count all eligible `S0` instances, `N1` those observed to reach `S1`, and `N2` those observed to reach `S2`. Report `N1/N0`, `N2/N1`, and **`N2/N0`**, along with the observation window, failure counts, and all candidate proposals. The identity `N2/N0 = (N1/N0) × (N2/N1)` is valid because these are nested outcomes in the **same cohort**. It does not license multiplying one paper's code-generation rate by another paper's connection rate. Also report attempts per accepted version; a rate conditioned on accepted candidates cannot answer how often initial instances complete the chain.

If a source lacks a model transcript, process lineage, activation record, or independent task result, mark that link **not shown**. Missing disclosure is not an observed failure; conversely, a product feature or analyst inference is not an observed success. In a future instrumented study, distinguish actual failures from telemetry loss and right-censoring when the time window ends. Disclose excluded or unobservable instances and sensitivity to how they are handled. Do not silently drop instances that crashed before a second attempt.

## Verification and comparison

Each accepted version needs an exact artifact hash or equivalent identity, an activation record from outside the candidate's editable success path, and a fresh task/result pair. The task must exercise a declared retained function; issuing it after activation prevents a stale response from the previous version from satisfying the check. Where practical, separately verify the targeted new behavior and a predeclared regression suite. A service probe tied only to a listening port or process does not verify the new code path.

A matched unchanged continuation can help estimate the effect of a revision over baseline task fragility. [SWE-Shift](mid-execution-change-audit-2026-11-26.md) offers a paired-prefix precedent for a single *external* change; it does not estimate a two-change model-authored chain. A future benign analogue can pair each branch at its pre-change state while preserving the full lineage and using independent current-version and retention checks. [Cao et al.](failure-detection-and-repair-audit-2026-11-26.md) motivate measuring whether the system notices a true failure before calling a repairer; [Wang et al.](revision-warrant-audit-2026-11-26.md) motivate checking that an alleged failure warranted the change. [BypassGym](https://arxiv.org/html/2611.13684) gives an example of a stronger single-candidate command/result oracle, but resets its endpoint between submissions.

These requirements are an **estimand and evidence standard**, not a feasibility probability. The reviewed public case ledger does not contain a cohort with all these fields.

The [runtime-intervention audit](runtime-intervention-boundary-audit-2026-11-26.md) explains why an intervening candidate may change state even if rejected and why live message or workflow revision results cannot be entered as executable-code activations.
