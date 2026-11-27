# Runtime AI in malware: evidence audit for red teams

Reviewed 2026-11-09; publication wording revised 2026-11-27. This audit tests four public cases against the Project Drexel research benchmark: a deployed program observes its environment, uses a model to decide what to change, applies that change, and keeps working through repeated revisions. The [feasibility assessment](drexel-feasibility-assessment.md) defines the stronger serial-code subclaim. The rankings below are research judgments, not claims about an actor's private intent.

## Evidence questions

1. **Model interaction:** Does the original report document a model call during an intrusion, a call reproduced during sample analysis, or only a call path inferred from code?
2. **Effect of output:** Did the response change an executed command, an interface action, a choice among existing functions, or the program's own code?
3. **Feedback:** Was a result of one action supplied to the model for another decision? A recurring request alone does not establish that the program learned from the previous outcome.
4. **Field use:** Was the behavior tied to a reported intrusion, or only to a sample, development build, or proposed design?

## Four-case audit

| Case | Model interaction and effect | Feedback and code change | Field-use evidence and limit |
| --- | --- | --- | --- |
| **LAMEHUG / PROMPTSTEAL** | [GTIG](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) reports that the running malware queried a hosted Qwen model and executed generated commands for predefined information and document collection. | The public account does not show command results being returned to the model for another decision. It reports later sample revisions, not model-driven self-rewriting by a deployed copy. | GTIG identifies APT28 use in live operations against Ukraine. [CERT-UA](https://csirt.csi.cip.gov.ua/en/posts/apt28-targets-security-and-defence-sector-with-ai-powered-software) independently describes the LAMEHUG campaign and LLM-based command generation, with **moderate confidence** APT28 attribution. Neither publishes a per-host sequence of successful calls and outcomes. |
| **PromptSpy** | [ESET](https://www.welivesecurity.com/en/eset-research/promptspy-ushers-in-era-android-threats-using-genai/) examined Android samples that supply current interface state to Gemini and use its response to choose the next interface action. The report includes an example response and follow-up state. | The sample sends an updated screen state back for another decision until a fixed interface goal is reached. This is a bounded action loop; ESET does not report program-code revision. | ESET had not observed the family in production telemetry. A possible distribution site and sample uploads do not establish a confirmed infection. [GTIG's later module analysis](https://cloud.google.com/blog/topics/threat-intelligence/ai-vulnerability-exploitation-initial-access) supports the family-level design, without a matched field event. |
| **PROMPTFLUX** | [GTIG's 2025 analysis](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) describes a model request for revised script code and active response logging. It also found a variant whose prompt requested an hourly rewrite. | In the analyzed sample, `AttemptToUpdateSelf` was commented out. The report does not demonstrate a response applied as a working new version, much less repeated successful revisions. | GTIG calls the family experimental, says it was in development or testing, and says its then-current state could not compromise a victim device or network. [GTIG's May 2026 summary](https://cloud.google.com/blog/topics/threat-intelligence/ai-vulnerability-exploitation-initial-access) lists dynamic modification and refers back to earlier experimentation; it adds no incident-level proof of a working self-update. |
| **CLOSEDQUORUM** | [Cisco Talos](https://blog.talosintelligence.com/the-closed-quorum-inside-the-first-reported-autonomous-ai-c2-implant/) recovered an implant whose code asks several model services to vote on a next action from a fixed set of functions. Static analysis and development builds establish the architecture. | The decision loop would use host context for later choices. Talos did not observe a complete end-to-end execution, and the report does not describe rewriting the implant's own code. | Talos had no confirmation of deployment. The public distribution build had placeholder credentials and a dummy webhook, so its model-driven operation was not demonstrated in that build. The case has no named APT attribution in the report. |

## Two different rankings

**Closeness to the expanded payload-changing benchmark, considering the reported design rather than deployment:**

| Rank | Case | Reason |
| --- | --- | --- |
| 1 | PROMPTFLUX | It alone requests rewritten source code. The observed implementation falls short of applying and validating that code. |
| 2 | PromptSpy | It shows a working model-guided loop that reacts to new environment state during analysis. Its changes are interface actions within a fixed goal. |
| 3 | CLOSEDQUORUM | Its architecture delegates recurring action choices to models, but a complete model-driven run was not shown. Its choices invoke existing functions. |
| 4 | LAMEHUG | It generates commands at runtime for fixed collection tasks. The public account does not show outcome-driven replanning or code revision. |

**Strength of public evidence that the reported model behavior actually ran:**

| Rank | Case | Evidence threshold reached |
| --- | --- | --- |
| 1 | LAMEHUG | Original investigators report use in live operations, with an independent campaign-level cross-check. Per-host call traces remain unpublished. |
| 2 | PromptSpy | ESET documents model responses and a follow-up interface state in sample analysis. Field deployment remains unconfirmed. |
| 3 | PROMPTFLUX | The sample contains a model request path and response logging; the self-update step is disabled in the analyzed copy. |
| 4 | CLOSEDQUORUM | The architecture is supported by static analysis and development builds; Talos could not complete the loop in the public build. |

The first ranking weighs similarity to **repeated autonomous adaptation**, including code change. The second weighs **observed execution and deployment**. They answer different questions. In particular, PROMPTFLUX's design similarity is not evidence that it worked in the wild.

## Claims that need careful reading

GTIG's [2025 overview table](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) summarizes PROMPTFLUX as self-regenerating, while the detailed analysis says the self-update function in the examined sample was commented out and the family lacked compromise capability. Its [May 2026 overview](https://cloud.google.com/blog/topics/threat-intelligence/ai-vulnerability-exploitation-initial-access) uses the dynamic-modification label without publishing an applied-revision trace. That later report comes from the same research organization, so it is not an independent replication of the earlier claim.

The title of [Talos's CLOSEDQUORUM report](https://blog.talosintelligence.com/the-closed-quorum-inside-the-first-reported-autonomous-ai-c2-implant/) calls it an autonomous implant. The body states that field use is unconfirmed and a complete end-to-end run was not observed. The architecture is a meaningful finding, with a narrower execution claim.

In this review, searches for follow-up original analysis did not identify an independently matched PROMPTFLUX artifact demonstrating successful self-revision or a CLOSEDQUORUM field trace demonstrating model-chosen actions. Later summaries and articles that repeat the original reports do not add a separate observation. This is a search result as of the review date, not a claim that such evidence cannot exist.

## What would close the expanded research gap

The missing public evidence is an incident-linked sequence showing **model request → code response → applied revision → continued correct operation**, repeated across revisions of the same deployed program. A credible report would also distinguish decisions made by the model from operator commands and identify the actual environmental feedback used for each change. None of these four cases establishes that full sequence.

For the wider actor comparison, see the [red-team case study](red-team-case-study.md), [2026 evidence update](2026-evidence-update.md), and [independent-source cross-check](corroboration.md).

The [PROMPTFLUX case file](promptflux-case-file.md) examines its variants and the limits of later sample-metadata reports in more detail.
