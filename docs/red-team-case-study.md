# Adaptation in three cases: a red-team study

Reviewed 2026-11-09. This brief is for authorized red teams studying adversary decision-making. It asks what outcome an actor pursued, which environmental constraint mattered, what changed after new information arrived, and who or what appears to have made the next decision. The "actor logic" below is an **analytical reconstruction**, not a quotation or proof of a particular operator's motive.

Only the LAMEHUG case is attributed to an APT in these sources: [CERT-UA](https://csirt.csi.cip.gov.ua/en/posts/apt28-targets-security-and-defence-sector-with-ai-powered-software) links its campaign to APT28 with moderate confidence, and [GTIG](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) reports APT28 use in live operations. PromptSpy is unattributed in [ESET's analysis](https://www.welivesecurity.com/en/eset-research/promptspy-ushers-in-era-android-threats-using-genai/). The 3AM case concerns a ransomware affiliate, according to [Bitdefender](https://www.bitdefender.com/en-us/blog/businessinsights/3am-ransomware-hybrid-ai-attack). They are compared for their decision patterns, not treated as one actor or campaign.

## The actor's decision problem

| Case | Outcome and operating condition | Adaptation point | What stayed fixed | Evidence limit |
| --- | --- | --- | --- | --- |
| **LAMEHUG / PROMPTSTEAL**, June 2025 | The reported goal was to collect system information and selected documents. The design outsourced the wording of commands to a hosted model. | The model returns commands during execution; the malware uses them for the specified collection tasks. | The task descriptions and collection objective are predefined. The reports do not describe the program choosing a new mission. | [GTIG](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools) labels the malware observed in operations, and [CERT-UA](https://csirt.csi.cip.gov.ua/en/posts/apt28-targets-security-and-defence-sector-with-ai-powered-software) corroborates the campaign and LLM-based command generation. Neither report gives a per-host sequence of model responses and resulting outcomes. |
| **PromptSpy**, February 2026 samples | The reported goal was to keep an Android app in the recent-apps list. Device interfaces differ, making one fixed sequence brittle. | The sample sends its current interface state to a model, acts on the response, and supplies the resulting state for another decision until the goal is met. | The goal and initial prompt are set in the sample. The behavior shown is interface navigation, not code rewriting. | [ESET](https://www.welivesecurity.com/en/eset-research/promptspy-ushers-in-era-android-threats-using-genai/) documented this loop in analysis but had not seen the malware in production telemetry. [GTIG](https://cloud.google.com/blog/topics/threat-intelligence/ai-vulnerability-exploitation-initial-access) assessed broader possible uses from the design; those uses were not verified field outcomes. |
| **3AM intrusion**, September 2026 | The affiliate pursued an intrusion across a UK school estate. Commands failed or needed revision during the hands-on phase. | Observed attempts included an unchanged retry, a small revision, and a switch of tool. The pace was similar across changes of different sizes. | The intrusion objective persisted; the report describes changes to the operator's command sequence, not to an implant's code. | [Bitdefender](https://www.bitdefender.com/en-us/blog/businessinsights/3am-ransomware-hybrid-ai-attack) observed the intrusion and retries. A human-and-model loop is its working interpretation. It could not inspect the originating machine or rule out a person manually passing results to a model. |

## Reconstructed actor logic

These statements are **hypotheses about the decision pressure** illustrated by each report. They are useful for red-team analysis without claiming access to an actor's private planning.

1. **LAMEHUG: preserve the objective, vary the command.** The actor-controlled task description specifies what information to obtain; the model supplies command text at runtime. The apparent tradeoff is flexible command generation coupled to an external model service. The public reports do not show a feedback cycle that evaluates failed commands and changes the objective. [GTIG's technical account](https://cloud.google.com/blog/topics/threat-intelligence/threat-actor-usage-of-ai-tools).
2. **PromptSpy: preserve the goal, react to the interface.** The next action depends on what the app currently sees. A result is fed back into the next model call, making the control loop visible in ESET's sample analysis. The meaningful adaptation is the selection of an interface action within a bounded goal. [ESET's analysis](https://www.welivesecurity.com/en/eset-research/promptspy-ushers-in-era-android-threats-using-genai/).
3. **3AM: preserve the intrusion task, revise the attempt.** The observed pattern is to retry, alter the command, or change the tool when progress stalls. The report supports that pattern in a real incident; it does not establish whether the next attempt came from a human, a model, or an automated controller. [Bitdefender's evidence and caveat](https://www.bitdefender.com/en-us/blog/businessinsights/3am-ransomware-hybrid-ai-attack).

## Questions for an adversary-emulation brief

For each pattern, a red team can document the following before an authorized exercise and compare the record with what actually happened:

| Question | Why it matters |
| --- | --- |
| What is the authorized objective, and which parts of it are fixed? | Separates a stable campaign goal from a changing method. |
| Which environmental observation can change the next decision? | Identifies whether the relevant input is host state, interface state, or the result of a prior attempt. |
| What is allowed to vary: command wording, interface action, operator workflow, or program code? | Prevents all variation from being described vaguely as "self-modifying malware." |
| Who makes each decision: human operator, model, fixed rule, or an unknown combination? | Keeps an AI attribution separate from the observation that a behavior changed. |
| What record would show the decision and its result? | Makes a claimed feedback loop reviewable; timestamps alone cannot establish its author. |
| What would count as a failed adaptation? | Records when a change produced no progress, rather than counting every retry as success. |

## Research conclusion

The strongest operational APT example here is **runtime command generation with a fixed collection goal**. The clearest analyzed feedback loop is **PromptSpy's interface-action selection**, with field deployment unconfirmed in the cited reports. The 3AM incident shows **iterative operator behavior** in a real intrusion, with the AI mechanism unresolved. None of the three shows a deployed program repeatedly rewriting and validating its own code, which remains the missing evidence for our [expanded *Drexel*-inspired hypothesis](drexel-feasibility-assessment.md).

For a wider comparison of campaign, build, developer, and runtime decisions, see [cross-actor patterns](cross-actor-patterns.md). The [runtime-AI evidence audit](runtime-ai-evidence-audit.md) tests LAMEHUG and PromptSpy alongside PROMPTFLUX and CLOSEDQUORUM against the *Drexel* self-changing-program claim.
