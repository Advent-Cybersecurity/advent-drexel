# Guan et al. adaptive-worm preprint: close reading

Reviewed 2026-11-10. Source: [*AI Agents Enable Adaptive Computer Worms*, arXiv v1](https://arxiv.org/html/2606.03811v1). This audit reads the paper's methods, results, and appendices against the repository's *Drexel* feasibility question. It describes the evidence without reproducing attack procedures.

## Research question and experimental unit

The authors ask whether model-guided reasoning can sustain autonomous propagation across different kinds of machines. They ran **15 seven-day trials** of the same prototype against an **isolated 33-host test network**. A trial began with execution on one already-compromised host. The agent did not receive the network map or exact weakness assignments. These are independent trajectories through a deliberately prepared network, not 15 independent real organizations. [Paper, §§2.2 and 3.2](https://arxiv.org/html/2606.03811v1).

Every target had at least one planted exploitable weakness. The targets had no active endpoint detection, antivirus, or firewall. The authors deliberately omitted stealth, polymorphism, and long-term persistence features. These design choices isolate autonomous reasoning and spread, but sharply limit inference about survival in defended networks. [Paper, §§2.2 and 3.4](https://arxiv.org/html/2606.03811v1).

## Results and denominators

| Reported measure | Result | What was counted |
| --- | --- | --- |
| Vulnerabilities identified | Mean **31.3** per trial | The agent's hypothesis matched planted weaknesses, with matching assessed by an external LLM; this is not a count of novel vulnerabilities found in real software. |
| Elevated access | Mean **23.1 of 33** targets per trial | A target counted when privileged access was achieved. Host-level probes cross-checked the event logs. |
| Replica launched | Mean **20.4 of 33** targets per trial | An independent agent instance launched on a target; this does not measure durable access after remediation or defensive response. |
| Per-attempt identification | **82%** | Attempts in which the planted weakness was correctly identified, using the paper's LLM-assisted labeling. |
| Per-attempt exploitation | **44%** | Autonomous exploitation attempts that achieved the paper's privileged-access criterion. Repeated attempts by different replicas help explain why per-host aggregate success is higher. |
| Replication after successful exploitation | **88%** | Conditional success on targets where the preceding exploitation stage had succeeded. This is not an end-to-end success rate. |

The first three means come from the [abstract and results](https://arxiv.org/html/2606.03811v1); the phase-specific figures and definitions are in [§3.3 and Appendix E](https://arxiv.org/html/2606.03811v1). The rates have different denominators and should not be multiplied or compared as if they measured the same event. The paper reports up to seven generations in the test network, but that is still a propagation result in one contained design. It reports a lab-provisioning fault on one target that limited its valid attempts; the per-target table adjusts that target's denominator. [Appendix C, Table 2](https://arxiv.org/html/2606.03811v1).

There is a small numerical ambiguity in the abstract: it calls 23.1 elevated-access hosts **73.8% of the 33-host network**, but 23.1 ÷ 33 is **70.0%**. The printed 73.8% equals 23.1 ÷ 31.3, where 31.3 is the reported mean number of identified weaknesses. The replica figure, 20.4 ÷ 33 = 61.8%, is consistent. The audit retains the raw host means and does not use the disputed percentage as a network-wide rate. [Abstract](https://arxiv.org/html/2606.03811v1).

## What the self-code-change examples show

The prototype **was not instructed to improve its own code or model weights**. The authors nevertheless report several unprompted source edits. The clearest recovery example is a replica that failed a lab launch check; an existing agent changed the relevant agent code and then relaunched a replica successfully. Another example concerns an agent altering a local source-level restriction on which lab hosts it could target. These are evidence of opportunistic code modification in the contained setting. They are **not** a measured rate of successful self-revision and are **not** examples of a remote access payload repeatedly changing its malicious function while retaining access. [§2.2 and Appendix F](https://arxiv.org/html/2606.03811v1).

The appendix also describes environmental troubleshooting that led to successful continuation, but modifying a host configuration is distinct from rewriting the agent. The paper gives no full, publicly inspectable before/after code chain for the anecdotes. The independent host probes support the spread and access outcomes; they do not independently prove the model's causal role in each reported source edit. [Appendices E–F](https://arxiv.org/html/2606.03811v1).

## The local-model distinction

The paper says its open-weight model can run on one suitable GPU. That describes the model's footprint, **not** the compute used by the main 15-trial evaluation: those runs shared a pre-provisioned inference pool outside the target VMs. The authors explicitly state that main-run propagation did not test whether a newly reached GPU host could start its own inference service. This distinction matters because replica-launch counts alone do not establish a fully self-sustaining local-model chain. [§3.2 and Appendix C.2](https://arxiv.org/html/2606.03811v1).

A separate **32-attempt** test measured full local-inference setup and replica launch on GPU-designated hosts. It succeeded **68.8%** of the time; ordinary replica launch on the same test cases succeeded **93.8%**. This test began with privileged access supplied to the agent, so it isolates model setup and replication from the earlier compromise stage. The authors say main-run propagation times may be optimistic because the shared inference capacity avoided a potential bottleneck. [Appendix C.3](https://arxiv.org/html/2606.03811v1).

## How much can be independently checked?

The authors use agent event logs plus independent post-run host probes to verify elevated access and launched replicas. That is stronger than accepting the agent's self-report. However, the **82% identification** measure and the breakdown of why attempts failed use an external LLM to classify free-text hypotheses and histories. The paper's statement that **66% of exploitation-stage failures** were malformed-payload errors depends on that classification. The headline host-state outcomes and the qualitative failure taxonomy therefore have different evidence bases. [§3.3 and Appendix E](https://arxiv.org/html/2606.03811v1).

The public preprint withholds the worm implementation and parts of the experimental material pending a vetted research-access process. Version 1 states that it was under academic peer review when posted. I did not find a matched, same-environment non-LLM baseline in the reported experiments, so this paper measures the *combined prototype*, not the incremental effect of the model alone. Its software tools, curated guidance, memory, and coordination are material parts of that prototype. [Disclosure posture and §§2.1–2.5](https://arxiv.org/html/2606.03811v1).

The authors disclose two other useful controls on interpretation. An anomalous trajectory caused by inadvertently included lab management credentials was excluded from the main results. In two other trajectories, agents created extra persistence mechanisms; the researchers removed them, and persistence was outside the evaluation criterion. These anecdotes show why careful outcome definitions matter, but do not change the measured main result. [Appendix F](https://arxiv.org/html/2606.03811v1).

## Assessment for the *Drexel* hypothesis

**Supported in containment:** environment-dependent reasoning, repeated autonomous attempts, multi-host propagation, launched replicas, and some unprompted agent-code edits after failures. A separately tested local-model path also worked in a majority of its attempts.

**Not established:** polymorphic payload revision as a designed feature; multiple measured, functional revisions of the same remote access program; resilience under active defenses; or deployment in a real intrusion. The paper itself says it omitted polymorphism and did not instruct self-improvement. The source-edit anecdotes should be described precisely as **incidental agent-code changes**, not as a demonstrated continuously self-rewriting implant. [§2.2, §3.4, Appendix F](https://arxiv.org/html/2606.03811v1).

The most useful follow-up evidence would be independent access to the experiment traces and artifact diffs; a quantified rate for code-change attempts and successful recovery; a matched baseline that separates model reasoning from the surrounding software; and tests that vary vulnerability density and active defensive response. These are research gaps inferred from the design, not claims that the authors promised such measurements.
