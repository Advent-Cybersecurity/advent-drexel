# ARTEX deployment of ZQAgent: a persistent-backdoor near case

Advent Cybersecurity source audit, 26 November 2026. Source: [NVISO Labs, *ARTEX leads to persistent ZQAgent backdoor*, 23 November 2026](https://blog.nviso.eu/2026/11/23/artex-fog0003-zqagent-backdoor/). This is a first-party incident-response and reverse-engineering account. No sample was downloaded or executed for this review.

## What the report establishes

NVISO says it observed an ARTEX-assisted intrusion deploy a previously undocumented Linux backdoor in Belgium. It describes an observed binary and related publicly submitted samples, a configured command-and-control destination, and code capabilities for command execution, file operations, tunneling, and persistence. The report calls the deployed result a long-lasting foothold. That is a first-party field assessment, stronger than a hypothetical framework feature, but it does not publish a time-ordered record of independent commands and corresponding results through a version transition.

The analyst says persistent-backdoor deployment by the LLM-driven tool was **believed** to be due to operator-specific instructions. This is an inference about the operator, not a published model transcript. The article does not attribute the backdoor's source-code authorship to a model or show a model request/response that produced a candidate ZQAgent version.

ZQAgent copies its existing executable image to an anonymous memory-backed file and then **restarts as a detached process** with a spoofed command line. That relocation changes how the process is launched and presented; the report does not say a model changed its executable behavior during the move. The reported persistence mechanisms likewise support recovery across starts, not same-process identity through two code revisions. Its operations to update runtime configuration are configuration changes, not published executable-code replacements.

## Four-link reading for Drexel

| Required link | Public evidence in this case |
| --- | --- |
| One continuing process through revisions | Unshown. The described memory relocation expressly restarts into a detached process. No later process lineage through code changes is published. |
| Model caused executable revision | Outside the reported sequence. ARTEX is associated with deployment, but model authorship of the implant or any *revision* is not traced. |
| Two distinct active resident code revisions | Unshown. Related sample hashes and available capabilities are not a two-version activation timeline in one process. |
| Independent remote-control result after each | Unshown. The first-party foothold claim and analyzed command handlers do not include an after-each-revision command/result pair. |

This case strengthens the narrower observation that an LLM-driven intrusion framework can be associated with **deployment of a persistent backdoor**. It does not change the verdict for two model-caused revisions of one continuing remote-access payload. It also shows why “in memory” should not be equated with “same process”: the reported mechanism deliberately starts a new process.
