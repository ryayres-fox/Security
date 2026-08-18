# Stepping stones — a security learning path

This repository is the output. This page is the **path that led to it** — written
for someone standing at the bottom of the ladder wondering how the rungs go.

It's drawn from two degrees a decade apart: a hands-on undergraduate program
(B.S. Network Security, 2011–2014) that taught **building and breaking**, and a
graduate program (M.S. Cybersecurity + M.B.A., 2016–2018) that taught **governing
and communicating**. But the credentials are not the point — the *order* is, and
**every rung below has a free or low-cost equivalent today.** You do not need
these exact programs. You need the rungs, roughly in order, and the discipline to
build something real at each one.

---

## The shape of it — two halves, both required

- **Build and break first.** Networking, then security, then forensics, then
  hands-on assessment. Lab-heavy, hands on keyboard. You cannot secure what you
  do not understand, and you understand a system by building it and taking it
  apart.
- **Then govern and communicate.** Policy, cryptography, detection, digital
  forensics, a capstone — and the business layer that lets you explain risk to
  people who do not do security.

You need both. An engineer who can't communicate risk stalls at senior; a manager
who can't build is fooled by a green dashboard. The gap between them is where most
security careers plateau.

---

## The rungs, in order — and how to climb each one today

| # | Stepping stone | Why it's load-bearing | Climb it today (free / low-cost) |
|---|---|---|---|
| 1 | **Networking fundamentals** — OSI, routing, subnetting, VLANs, DNS | Everything sits on the network; every later skill assumes it | Professor Messer Network+ · subnet by hand · build a topology in GNS3/Packet Tracer |
| 2 | **Systems & hardening** — Windows/Linux admin, config baselines (STIG, CIS/USGCB), GPO | Most real-world risk lives in *configuration*, not exotic exploits | CIS Benchmarks + DISA STIGs (free) · harden a throwaway VM and diff it |
| 3 | **Security specialization** — firewalls, VPN, IDS/IPS (Snort/Suricata), segmentation | The defensive toolkit and where zero-trust starts | Security+ · TryHackMe / Hack The Box · run Snort/Suricata in a home lab → [`../homelab/`](../homelab/) |
| 4 | **Digital forensics & IR** — evidence handling, disk/memory analysis, incident response | When prevention fails, someone has to reconstruct what happened | Autopsy (the free FTK-equivalent) · DFIR labs · the GCIH / GCFA path |
| 5 | **Offensive & assessment** — vuln assessment, scanning, wireless, pen-test methodology | You defend better once you've attacked; assessment turns opinion into evidence | GPEN / OSCP path · scoped targets in a lab you own · write the report, not just the exploit |
| 6 | **Governance, risk & compliance** — CIA triad, risk, policy, BCP, control frameworks | Controls without governance are hobbies; frameworks make coverage computable | NIST 800-53 / RMF, ISO 27001 (free to read) · CISSP · see [`control-mapping.md`](control-mapping.md) and [`../reference-architecture/`](../reference-architecture/) |
| 7 | **Communication & management** — writing, briefing, risk translation | A finding nobody can act on didn't happen | Write a [threat model for non-experts](threat-model.md) · practice the "headline you'd say publicly" · the MBA layer is really *decision-making under uncertainty* |

---

## The quiet foundation nobody lists: statistics

Undergrad math and statistics (including R) looked like a detour at the time. It
was not. Security is increasingly a **data problem** — findings normalization,
run-over-run [delta analysis](operating-the-scan-flow.md), detection tuning,
separating signal from base rate. A working grasp of basic statistics and a
scripting language ages better than any single tool.

*Climb it today:* basic stats + Python/pandas, applied to real log or findings
data.

---

## It's a spiral, not a checklist

You do not finish rung 1 and leave it behind. You **revisit networking** when you
learn cloud VPCs, **revisit forensics** when you get into detection engineering,
**revisit governance** when you map controls to code. Each pass is deeper because
the ones above it give it context.

- The [home lab](../homelab/) is where you keep climbing after the coursework
  runs out — a place to break things you can't break at work.
- [Staying current](staying-current.md) is how you keep the top of the ladder
  from going stale.
- This repository is what the top of the ladder builds: standards enforced as
  code, evidence that falls out of the pipeline, controls you can prove ran.

**You don't need the degrees. You need the rungs — and something built at each
one to show for it.**
