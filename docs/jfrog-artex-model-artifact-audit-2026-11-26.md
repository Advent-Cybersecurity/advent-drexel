# ARTEX-linked malicious model artifacts: rapid external iteration

Advent Cybersecurity source audit, 26 November 2026. Source: [JFrog Security Research, *The Agent That Robbed Itself*, 24 November 2026](https://research.jfrog.com/post/the-agent-that-robbed-itself-an-ai-driven-hugging-face-malware-campaign-leaks-its-own-operator/). The source is a first-party artifact and public-repository-history analysis. No model, sample, or malicious repository was run in this review.

## Observed sequence and attribution strength

JFrog reconstructs the first malicious model repository's commit sequence: model files uploaded, a collection result committed from the operator's own host 14 seconds later, an overwritten self-test result, a second collection result, and quick packaging and test-marker changes. Roughly five hours later, the same account under a different display name published a second, differently packaged malicious model and separate empty collection repository. It also published nine tokenizer probe repositories in between. This is evidence for **rapid external artifact iteration and an operator-side functional self-test**, not a longitudinal resident payload update on a victim.

The leaked operator-side result exposed an ARTEX process, model-provider configuration, and task working directories. JFrog assesses with high confidence that an ARTEX agent task created, uploaded, and tested the malicious models. The report explicitly says the evidence cannot separate choices made by the LLM from instructions given by the human operator. It does not publish a complete model request/response mapped to each source delta. The first result came from the operator's own container; JFrog found no other collection artifacts in its index, and the later collection repositories were empty when Hugging Face disabled the set. Thus the observed test must not be described as a confirmed external victim compromise.

The second model changed packaging and collection details while preserving the broad collection-and-exfiltration goal. JFrog says the final commit made its configuration invalid under stock `transformers`, so that **latest commit was disarmed in the ordinary loader path**; an earlier revision remained available until takedown. This is an especially useful promotion-versus-proposal warning: a later artifact and a changed code file do not establish a working latest version. The observed scanner badges also do not prove that the agent noticed them or that every change was caused by feedback from a scanner.

## Drexel link check

| Required link | Status in published record |
| --- | --- |
| One continuing remote-access process | Outside this setting. Repositories and operator-side tests are separate artifacts and invocations. |
| Model caused executable payload revision | First-party **agent-task attribution** is strong, but exact response-to-edit provenance is not published. Artifact revisions are observed; model causation for each specific edit is reported or inferred, not directly traced. |
| Two revisions active in that one process | Outside this setting. Commits and self-tests do not show in-place adoption by a continuing victim program. |
| Independent remote-control result after each | Outside this setting. The test showed collection/exfiltration from the operator's own container, not after-change remote-control commands in a resident implant. |

This case strengthens the feasibility of **fast agent-associated artifact generation, testing, and adaptation** and reveals a concrete failure of the latest artifact under a common loader. It supplies no rate for Drexel's serial same-process chain and no evidence that the model itself resided on an endpoint.
