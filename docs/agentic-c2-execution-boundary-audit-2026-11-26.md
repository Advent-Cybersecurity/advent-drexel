# Agentic C2 demonstrations: control loop versus code revision

Advent Cybersecurity source audit, 26 November 2026. This is a reading of two original BeyondTrust Phantom Labs demonstrations, not a reproduction. No model, agent, or payload was run. The question is whether a demonstrated model-directed remote-control task also demonstrates model-authored changes to the resident program.

## Claude & Control

In [the 9 April original report](https://www.beyondtrust.com/blog/entry/claude-control-agentic-c2-computer-use-agent), the researcher describes a C# implant that polls an Azure blob for operator instructions, sends desktop context through an Azure Function proxy to the Claude API, and executes returned computer-use actions on a Windows test endpoint. The agent loop is local to the endpoint, but **model inference is cloud-hosted**. The author reports working browser and filesystem interactions. He also reports that this approach generated no Microsoft Defender for Endpoint or CrowdStrike alerts in his testing. The article does not specify a complete trial count, endpoint configuration/policy, product versions, observation interval, or raw alert telemetry. Its no-alert observation is consequently specific to the reported demonstration, not an evasion rate or guarantee.

The article presents the implant as researcher-written code. Claude chooses actions within exposed tools; no model-authored change to the implant executable, live module replacement, version hash sequence, or after-update command/result is reported. The author explicitly notes an interactive-session dependency for desktop control, occasional agent mistakes, token cost, and a manual browser-approval boundary in one explored path. This is useful evidence that a model can drive an already running C2-like control loop, while leaving Drexel's self-revision claim open.

## Hook-based control path

In [the 6 October hook demonstration](https://www.beyondtrust.com/blog/entry/claude-code-hooks-c2-skill-security), the researcher describes a malicious skill hook that runs before selected coding-agent tool calls, polls a remote tasking endpoint, and returns output. Here the executable hook is **attacker-prepared script code** launched by the host agent's hook mechanism; the model need not choose, inspect, or author its actions. Each hook invocation launches a child process. A continuing agent session and repeated hook firings do not by themselves establish one continuously resident hook process, much less two model-caused active code revisions in it. The post discusses process/network/file signals, so its demonstration should not be converted into a claim that this route is universally invisible to endpoint monitoring.

## Placement in the feasibility argument

These two demonstrations add primary examples for the **remote tasking** component and illustrate a distinct supply-chain/hook route to code execution. They do not fill the joined evidence gap: exact model-to-code provenance, two accepted active versions in an identified continuing program image, and an independent remote task/result after each. The first uses cloud inference; the second need not involve model causation for the hook's C2 behavior. Neither can be used to estimate Drexel's serial-revision probability or local model resource cost.
