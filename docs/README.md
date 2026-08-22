# docs

Index for anyone who landed here directly. The repository's front page
([`../README.md`](../README.md)) threads these into a reading order; this is the
flat list, grouped by what you're trying to do.

## Choosing and running scanners

- [`scanner-strategy.md`](scanner-strategy.md) — what each scanner is *for*, the sequencing, and when **not** to use each one
- [`without-a-commercial-platform.md`](without-a-commercial-platform.md) — the open-source estate vs. Wiz/Tenable: capability by capability, and where it stops
- [`azure-resource-graph-hunting.md`](azure-resource-graph-hunting.md) — hunting Azure exposure (public IPs, any/any SSH/RDP, Defender misconfig, drift) with free, agentless KQL
- [`operating-the-scan-flow.md`](operating-the-scan-flow.md) — running it at scale: authorization, scan-volume blow-up, runner/SLA limits, the kiosk-runner pattern

## Reviewing, governing, responding

- [`review-standard.md`](review-standard.md) — what *code changes* need a security review, and how a hold clears
- [`software-review-template.md`](software-review-template.md) — a fill-in intake for anything you *bring in* (apps, integrations, vendors)
- [`threat-model.md`](threat-model.md) (for non-specialists) + [`threat-model-method.md`](threat-model-method.md) (the reusable method)
- [`writing-detections.md`](writing-detections.md) — making a detection a *control*: a schema, a severity×frequency score, and a validation gate that fails a malformed detection before it ships
- [`memory-forensics.md`](memory-forensics.md) — reading a machine's live state from a RAM capture (Volatility): acquire-first, prove the OS, walk processes → network → artifacts
- [`malware-triage.md`](malware-triage.md) — detonating a suspicious file in a sandbox without lying to yourself: isolation, routing trade-offs, and the ways a clean-looking run is a blind one
- [`incident-response.md`](incident-response.md) — a 2017 swimlane process modernised to NIST 800-61r3 / CSF 2.0 (before → after)
- [`silent-failure-patterns.md`](silent-failure-patterns.md) — controls that report success while enforcing nothing
- [`control-mapping.md`](control-mapping.md) — how controls are declared next to the code and folded into a report
- [`branching.md`](branching.md) — how changes get in

## Learning and giving back

- [`stepping-stones.md`](stepping-stones.md) — a security learning path with at-home labs and a toolbench
- [`virtual-lab.md`](virtual-lab.md) — standing up an isolated VirtualBox lab (Kali + a vulnerable target) to practice against, host-only and snapshot-safe
- [`staying-current.md`](staying-current.md) — the automated briefing habit; currency as a control
- [`agentic-skills-top-10.md`](agentic-skills-top-10.md) — the OWASP Agentic Skills Top 10 (AST10) mapped to this repo's AI-security controls
- [`federal-hacs/`](federal-hacs/) — GSA HACS / federal-compliance study set (cheat sheet, study guide, flashcards)

## Generated — do not hand-edit

These are produced by [`../tools/`](../tools/) and diffed in CI; a stale copy fails the build.

- [`control-coverage.md`](control-coverage.md) — the coverage report, generated from every `controls.yaml`
- [`metrics.md`](metrics.md) — the repository's own metrics, every number with its unit named
- [`diagrams/`](diagrams/) — every SVG, drawn from data in `render_diagrams.py`, not exported from a tool
