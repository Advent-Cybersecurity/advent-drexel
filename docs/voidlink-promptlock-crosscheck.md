# VoidLink and PromptLock: development, deployment, and runtime AI

Reviewed 2026-11-10. These cases sharpen the [*Drexel* feasibility question](drexel-feasibility-assessment.md): did a model change a running remote access program's payload, or did it help build the program before use? The reports below are original investigations. Their observations refer to different versions, time periods, and evidence types.

## VoidLink chronology and version boundary

| Source and date | What investigators observed | Limit for the AI claim |
| --- | --- | --- |
| [Check Point Research, January 13, 2026](https://research.checkpoint.com/2026/voidlink-the-cloud-native-malware-framework/) | Investigators analyzed developing VoidLink samples, including environment-dependent behavior, configurable modules, and an option that decrypts protected code regions while in use. They stated that they had **not observed real-world infections** at the time of publication. | Environment-dependent rules and loading modules do not establish that an AI model chose or wrote changes during execution. Decrypting and re-encrypting existing code regions is not evidence of model-generated source revision. |
| [Check Point Research, January 20, 2026](https://research.checkpoint.com/2026/voidlink-early-ai-generated-malware-framework/) | An exposed development environment yielded TRAE IDE helper files, planning documents, and source code. Check Point compared the recovered specifications with the code and reported a working test artifact dated December 4, 2025. It assesses that AI drove much of the **development**. | The investigators did not have the full model conversation. The report does not show an implant calling a model after deployment, and the recovered planning artifacts concern a later development phase. |
| [Cisco Talos, February 10, 2026](https://blog.talosintelligence.com/voidlink/) | Talos reports multiple VoidLink-related victims from September 2025 through January 2026 and tracks the operators as UAT-9921. It assesses that the earlier activity used version 1.0, whereas Check Point's dated development files concerned version 2.0. Talos says it did **not** see AI-enabled tools used in compromise or post-compromise activity. | This establishes reported field use of the **framework family**, but does not prove that the deployed version was produced by the later AI-assisted development process. Talos says it cannot rule out authorized red-team exercises for some activity. |

The apparent conflict between “no infections observed” and “multiple victims” is a difference in investigative visibility and publication timing. It should not be resolved by silently combining Check Point's version 2.0 developer artifacts with Talos's version 1.0 field observations. Talos describes compile-on-demand support as a foundation for possible future AI-enabled tooling; its proposed agent integration is a **forecast**, not an observed VoidLink model loop.

**Assessment:** VoidLink provides unusually strong evidence of AI-assisted malware *development* and separate evidence of field use of an earlier version. The public reports do not connect AI-generated code revisions to a running implant in the reported victims.

## PromptLock and the local-model question

[ESET Research, August 26, 2025](https://www.welivesecurity.com/en/ransomware/first-known-ai-powered-ransomware-uncovered-eset-research/) analyzed PromptLock samples that used a locally accessible language model through an API to generate scripts during execution. This is direct sample evidence that a local-model arrangement is technically possible. ESET said the samples were **not seen in actual attacks** and considered them a proof of concept or work in progress. It did not report the fixed main program rewriting itself and maintaining a revised remote access function.

On September 3, ESET updated its article after contact from the authors of [*Ransomware 3.0*](https://arxiv.org/abs/2508.20444), whose prototype closely resembled the PromptLock samples. The public wording supports a likely relationship, but does not prove exact artifact identity. These should therefore not be counted as two independent field deployments.

## Evidence gained

The new distinction is **version linkage**. A family can have AI-assisted development artifacts and separately have victims without proving that the observed victims received the AI-developed version. Conversely, PromptLock demonstrates runtime model-generated scripts in samples without proving deployment. Neither fills the incident-linked sequence of model output, applied revision of the same remote access payload, and continued operation across repeated revisions.
