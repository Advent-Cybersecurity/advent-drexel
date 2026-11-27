# Local-model and runtime-change claims: source audit

Reviewed 2026-11-09. The [*Drexel* feasibility assessment](drexel-feasibility-assessment.md) asks whether a deployed remote access program used AI to modify its payload and kept working. This note examines a newly found field claim about local AI inference, alongside two cases that help distinguish model placement from malware behavior.

## Mandiant's September 2026 case study

In [“AI risk and resilience in 2026,” case study 4](https://cloud.google.com/security/resources/ai-risk-and-resilience-2026), Mandiant says it observed campaigns using embedded, lightweight AI models in victim networks. It says the malware used local inference to assess host security tools and changed its own command-execution strings at runtime. The report presents this as an observed campaign behavior, not a proposed design. **This is the strongest field-use assertion of local model-driven runtime change found in this review.**

The public case study does not identify an actor, malware family, affected incident, model type, date of activity, sample, before-and-after command strings, inference trace, or repeatable revision sequence. It does not say that the model is an LLM. It describes changes to command strings and action syntax; that is narrower than demonstrated rewriting of an implant's source code or binary. We therefore record Mandiant's claim as a **first-party field assertion without published artifacts sufficient to independently verify the mechanism**. It raises the priority of this lead, but it does not close the repository's evidence gap for repeated, functional payload revisions by one deployed remote access program.

The same [Mandiant report's case study 2](https://cloud.google.com/security/resources/ai-risk-and-resilience-2026) describes a different arrangement: an attacker used LLMs on a compromised cloud VM to iteratively debug and improve offensive tooling during an intrusion. That is live, AI-assisted operator development in attacker-controlled infrastructure. The report does not present it as an autonomous model loop inside a deployed implant.

## Two checks on terminology

| Original investigation | What it establishes | What it does not establish |
| --- | --- | --- |
| [GTIG, September 2026](https://cloud.google.com/blog/topics/threat-intelligence/from-prompting-to-autonomy-the-evolution-of-adversarial-ai), “Threat Actors Targeting Proprietary AI Research and Models” | GTIG reports suspected UNC6508 activity compromising cloud environments to deploy local, open-weight LLM infrastructure. This is evidence that an actor may run a local model using compromised compute. | The report does not connect that model to a malware sample, on-host payload revision, or repeated self-modification. “Local model” describes where inference runs, not what a deployed program does with its output. |
| [IBM X-Force, March 2026](https://www.ibm.com/think/x-force/slopoly-start-ai-enhanced-ransomware-attacks), “Slopoly” | X-Force found a functioning PowerShell backdoor during a Hive0163 ransomware intrusion and says it maintained access for more than a week. The team infers LLM-assisted development from script artifacts. | Although the script calls itself polymorphic, X-Force explicitly says it cannot modify its own code while running. The builder was not recovered, and AI authorship is an inference, not a model transcript. |

## Current conclusion

Mandiant's case study changes the wording of the evidence assessment: there **is** now a first-party public claim of local AI-driven runtime change in malware used in campaigns. The published account does **not** supply the artifact chain needed to audit that claim or determine whether it matches *Drexel*'s AI-modified remote access payload. GTIG's local-model observation and IBM's deployed backdoor are separate cases; neither corroborates Mandiant's mechanism. The next useful evidence would be an original case report with a named sample or incident and the sequence linking model input, output, applied change, and continued function. This is an evidence request, not an implementation plan.
