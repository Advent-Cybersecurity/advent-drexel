# Cross-case synthesis of the serial-revision claim

Advent Cybersecurity working note, 26 November 2026; publication wording revised 27 November. This is a descriptive analysis of the [31 selected cases](../data/closest-case-claim-ledger-2026-11-26.json), not a sample of all malware or all studies. The [search protocol](source-search-and-evidence-protocol-2026-11-26.md) explains selection and the ledger defines each status. Cases were selected for proximity to at least one component of the Project Drexel hypothesis or as explicit boundary comparators. The source registry is a heterogeneous bibliography and is not a case denominator.

## What the selected public cases actually connect

The expanded hypothesis requires four links in **one time-ordered record**: an identified continuing remote-access process; exact model causation for a payload-code revision; two distinct revisions that became active in that process; and an independently issued remote task with a corresponding result **after each** activation. A report cannot supply the chain by combining its unrelated incidents, different builds, separate model trials, or distinct RAT families.

| Source cluster | Strongest useful observation | Missing joined link |
| --- | --- | --- |
| [Kitsune](https://www.cs.tufts.edu/~jfoster/papers/toplas-kitsune.pdf) and [RSInfer](https://github.com/open-agent-infra/RSInfer/blob/bd26c7e1554211a578e733f7e2fc59feb3a21452/doc/rsi/2026-11-11-real-kernels-hot-apply.md) | Benign systems document serial code activation, with Kitsune's continuing driver and RSInfer's version-specific inference outputs. | Neither supplies a model-authored remote-access payload with after-each remote-command results. RSInfer's process continuity is author-reported without independent PID telemetry. |
| [cl-agent's checked-in conversation](cl-agent-live-extension-trace-audit-2026-11-26.md) | The model submitted and loaded an extension, then loaded a byte-distinct revision in the same recorded conversation; the revised memory tools were invoked afterward. | The first load adds a new extension; no OS PID/image record, function check between loads, or remote-control workload is published. |
| [EyeSpy](https://web.archive.org/web/20231008233626id_/https://www.hyas.com/hubfs/HYAS_EyeSpy_Proof_of_Concept.pdf), [Gödel Agent](https://arxiv.org/html/2410.04444), and [Shirudo](shirudo-live-shield-audit-2026-11-26.md) | Model-proposed or model-generated code can feed an in-process replacement mechanism or a reportedly live defensive attachment. | No source joins two accepted model-authored versions to retained remote control; EyeSpy's successful module followed repair attempts, and Shirudo describes one guard. |
| [Yuan et al.](https://arxiv.org/html/2608.01639v1) and [BypassGym](https://arxiv.org/html/2611.13684) | Controlled candidate work can check individual endpoint or control-channel outcomes. | Fresh or restored endpoints reset the process between candidates, so outcomes are not conditional on an earlier active version. |
| [COGENT](cogent-endpoint-claim-audit-2026-11-26.md) | The conference abstract reports mutation cycles; a related thesis abstract reports 45 bidirectional endpoint workflows. | Accessible abstracts do not bind the two claims to one experiment, process, version sequence, or after-each result; full methods were unavailable. |
| [SilkParasite](silkparasite-plugin-result-audit-2026-11-26.md) | Field RATs have in-memory module-loading and C2 result paths. | Different families provide different status semantics; no model-to-module trace or two-version same-instance result chain is published. |
| [Unit 42's agentic campaigns](unit42-agentic-webshell-boundary-2026-11-26.md) | Field agents produce many fresh scripts and multiple web-shell variants through persistent footholds. | A process **chain**, many paths, and two comment-language artifact versions do not identify one process accepting two functional code revisions. |
| [Amazon's Cairn shell case](aws-cairn-shell-process-boundary-2026-11-26.md) | First-party controller inspection supports reported agent-directed payload creation and a working root shell. | The one shell file was imported by a newly spawned Python process; exact model-to-artifact bytes and a two-version resident chain are unpublished. |

The ledger's annotation totals make the gap visible, but they are **reviewer classifications of selected cases, not success frequencies**:

| Required link | Documented | First-party reported | Mechanism only | Not shown | Outside evaluated scope |
| --- | ---: | ---: | ---: | ---: | ---: |
| Continuing process | 2 | 5 | 8 | 9 | 7 |
| Model to executable revision | 5 | 10 | 5 | 5 | 6 |
| Two active-and-functional revisions | 2 | 1 | 1 | 19 | 8 |
| Remote-control result after each | 0 | 0 | 0 | 14 | 17 |

These rows cannot be multiplied, pooled into a confidence score, or read as fractions of real-world attempts. `Outside evaluated scope` is substantively different from `not shown`: a benign service has no remote-control workload by design, whereas a field report may simply omit a relevant event. `Documented` applies to that **one link** and its stated unit; it never means the entire four-link claim is documented. The last row explains the current bounded negative finding: none of the 31 selected public case records provides an after-each **version-bound remote-control result**.

## How to use this in the paper

Present the closest cases as **noninterchangeable components**. The strongest process/version demonstrations are benign; the strongest field remote-access architectures lack exact model-to-version provenance; the best model-guided endpoint evaluations reset between candidates. If later evidence joins the missing events, update the individual case and the conclusion. Until then, say that the integrated Project Drexel hypothesis is technically plausible but **unestablished in this reviewed public record**.
