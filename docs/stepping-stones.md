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
| --- | --- | --- | --- |
| 1 | **Networking fundamentals** — OSI, routing, subnetting, VLANs, DNS | Everything sits on the network; every later skill assumes it | [Professor Messer](https://www.professormesser.com/)'s free Network+ videos · subnet by hand · build a topology in GNS3 / Packet Tracer |
| 2 | **Systems & hardening** — Windows/Linux admin, config baselines (STIG, CIS/USGCB), GPO | Most real-world risk lives in *configuration*, not exotic exploits | CIS Benchmarks + DISA STIGs (free) · harden a throwaway VM and diff it |
| 3 | **Security specialization** — firewalls, VPN, IDS/IPS (Snort/Suricata), segmentation | The defensive toolkit and where zero-trust starts | Security+ · TryHackMe / Hack The Box · run Snort/Suricata in a home lab → [`../homelab/`](../homelab/) |
| 4 | **Digital forensics & IR** — evidence handling, disk/memory analysis, incident response | When prevention fails, someone has to reconstruct what happened | Autopsy (the free FTK-equivalent) · DFIR labs · the GCIH / GCFA path |
| 5 | **Offensive & assessment** — vuln assessment, scanning, wireless, pen-test methodology | You defend better once you've attacked; assessment turns opinion into evidence | GPEN / OSCP path · scoped targets in a lab you own · write the report, not just the exploit |
| 6 | **Governance, risk & compliance** — CIA triad, risk, policy, BCP, control frameworks | Controls without governance are hobbies; frameworks make coverage computable | NIST 800-53 / RMF, ISO 27001 (free to read) · CISSP · see [`control-mapping.md`](control-mapping.md) and [`../reference-architecture/`](../reference-architecture/) |
| 7 | **Communication & management** — writing, briefing, risk translation | A finding nobody can act on didn't happen | Write a [threat model for non-experts](threat-model.md) · practice the "headline you'd say publicly" · the MBA layer is really *decision-making under uncertainty* |

---

## What college actually gave me — and how to recreate it for free

The value was never the campus or the brand. It was two things, and **you can
reproduce both at home for the cost of a laptop:**

1. **A sequenced path.** Someone had ordered the learning so each lab stood on the
   last — network before security, security before assessment. That structure is
   the whole point of this page; the rungs above *are* the path.
2. **Enforced documentation.** Every lab ended in a written artifact — what I did,
   what I found, and the risk. That discipline, not the tools, is what turns
   "I messed around with Kali one weekend" into something an employer recognises.

The single most valuable thing college taught was **proving and documenting an
issue and its risk** — not exploiting a box, but writing up the finding so someone
who wasn't there can understand it, believe it, and act on it. You do **not** need
an enterprise to practise that. You need a target you own, and the discipline to
write it up as if it will land on a manager's desk.

**Experience is experience.** A vulnerability you found in your own lab, scoped and
documented honestly, is real experience — the same skill, the same artifact, just a
smaller blast radius. Do it ten times and you have a portfolio, not a hobby.

## Four labs you can run at home

All free or nearly so. For each: what to stand up, a first exercise, and — the part
that matters — **what to document.**

> **Authorization first, always.** Only ever test systems you own or are explicitly
> permitted to test. That boundary is not a formality — it's the line between
> practice and an incident (see [operating the scan flow](operating-the-scan-flow.md)).

### Networking lab

- **Stand up:** GNS3 / EVE-NG / Packet Tracer, or two cheap VMs behind
  pfSense/VyOS.
- **Do:** segment a network into VLANs, route between them, put a firewall in the
  path with default-deny, add a VPN (WireGuard/OpenVPN) — then deliberately break
  connectivity and diagnose it back to health.
- **Document:** a topology diagram, an addressing plan, and a change log —
  *what I changed, why, and what broke.* (That is exactly how the diagrams in
  [`../homelab/`](../homelab/) and [`../reference-architecture/`](../reference-architecture/)
  begin.)
- *Signpost:* Network+ covers the fundamentals this rung assumes.

### Forensics lab

- **Stand up:** [Autopsy](https://www.autopsy.com/) (free — the FTK-equivalent),
  plus a practice image (NIST CFReDS, public DFIR images, or one you make yourself
  with FTK Imager / `dd`).
- **Do:** acquire an image **and record its hash**, analyse it in Autopsy — recover
  deleted files, build a timeline, pull artifacts — then re-verify the hash to prove
  nothing changed.
- **Document:** an evidence log (source, acquisition method, hash, examiner, date),
  findings with screenshots, and a plain-language conclusion. Handle it as if it
  could go to court — the **chain-of-custody discipline is the skill**, not the tool.
- *Signpost:* the GCFA / GCFE path formalises digital forensics.

### Pentesting lab

- **Stand up:** a hypervisor + Kali + deliberately-vulnerable targets —
  Metasploitable 2, VulnHub boxes, or TryHackMe / Hack The Box for guided paths;
  DVWA / OWASP Juice Shop for web.
- **Do:** work a real methodology (PTES / OSSTMM) end to end —
  recon → scan (`nmap`) → identify → exploit (Metasploit, Burp Suite CE) →
  post-exploit — so it's structured, not a scavenger hunt.
- **Document:** a **vulnerability report** — the finding, evidence and repro steps,
  a **risk rating** (impact × likelihood), and remediation. The write-up is the
  deliverable; the exploit is just how you earned it.
- *Signpost:* the GPEN / OSCP path formalises this rung.

### Defense, hardening & detection lab

The other side of the pentest — and the one hiring managers ask about most, because
it's what you'll actually do on the job.

- **Stand up:** a VM to harden against a baseline (CIS Benchmarks / DISA STIGs),
  an IDS (Snort / Suricata), and a place to send logs (Security Onion, or
  Wazuh / ELK / Splunk Free).
- **Do:** harden the box and **diff it against the un-hardened baseline**; then
  generate traffic (replay a pcap, run your pentest lab at it) and **write a
  detection** that catches it — and confirm it *fires* on the attack and *stays
  quiet* on normal traffic.
- **Document:** a hardening diff (what changed, mapped to the benchmark control),
  the detection rule, and tuning notes — *why this threshold, what it misses.*
  A detection you can't prove fires is the same silent-failure this repo is built
  around ([silent-failure patterns](silent-failure-patterns.md)).
- *Signpost:* Security+ for the fundamentals, GCIA/GCIH for detection and response.

The academic version of these used named methodologies and ended in formal
reports — and that structure is the reusable part. Skip the grade; keep the rigor.

## The one habit that turns practice into experience

Every lab ends in an artifact **a stranger could act on** — not notes to yourself,
a report: what you tested, what you found, the risk in business terms, and the fix.
That is the standard college enforced, and the one you can enforce on yourself for
free. It is also the whole argument of this repository:
[communicate risk to non-experts](threat-model.md), and make the evidence something
someone can pick up and use.

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

---

## Appendix — a learner's toolbench

Everything below is free or low-cost. The column that matters is **the artifact**:
that is what turns "I used the tool" into experience someone will hire. The
**signpost** cert is exactly that — a marker you're on the path, not a prerequisite
to start.

| Track | Build / analyse with | Practice targets | Your artifact | Signpost |
| --- | --- | --- | --- | --- |
| **Networking** | GNS3 · EVE-NG · Packet Tracer · pfSense / VyOS · WireGuard / OpenVPN · VirtualBox / Proxmox | your own VLANs & topology | topology diagram + addressing plan + change log | Network+ |
| **Systems, hardening & detection** | CIS Benchmarks · DISA STIGs · Snort / Suricata · Security Onion · Wazuh / ELK · Splunk Free · Wireshark | a VM you harden; traffic you generate/replay | hardening diff (mapped to controls) + detection rule + tuning notes | Security+ · GCIA |
| **Forensics / DFIR** | Autopsy · FTK Imager · `dd` · Volatility · Wireshark | NIST CFReDS · public DFIR images · images you make | evidence log + hash / chain of custody + findings write-up | GCFA / GCFE |
| **Pentesting** | Kali · nmap · Metasploit · Burp Suite CE · Nikto · Hydra | Metasploitable 2 · VulnHub · TryHackMe · HTB · DVWA / Juice Shop | vulnerability report + risk rating + remediation | GPEN / OSCP |
| **Governance & comms** | NIST 800-53 / RMF · ISO 27001 · STRIDE threat modelling | your own lab findings | control mapping · [threat model](threat-model.md) · risk brief | CISSP |
| **Analytics** (cross-cutting) | Python / pandas · R · basic statistics | your own log / findings data | trend & [delta analysis](operating-the-scan-flow.md) | — |

### Where these live

Every resource above is real, free (or has a free tier), and one click away — so
none of it has to be taken on faith.

- **Learn / guided:** [Professor Messer](https://www.professormesser.com/) (free CompTIA video
  courses) · [TryHackMe](https://tryhackme.com/) · [Hack The Box](https://www.hackthebox.com/)
- **Build networks:** [GNS3](https://www.gns3.com/) · [pfSense](https://www.pfsense.org/) ·
  [VyOS](https://vyos.io/) · [WireGuard](https://www.wireguard.com/) · [OpenVPN](https://openvpn.net/)
- **Harden & detect:** [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) ·
  [DISA STIGs](https://public.cyber.mil/stigs/) · [Snort](https://www.snort.org/) ·
  [Suricata](https://suricata.io/) · [Security Onion](https://securityonionsolutions.com/) ·
  [Wazuh](https://wazuh.com/)
- **Forensics:** [Autopsy](https://www.autopsy.com/) · [Volatility](https://volatilityfoundation.org/) ·
  [NIST CFReDS test images](https://cfreds.nist.gov/)
- **Pentest & targets:** [Kali](https://www.kali.org/) · [nmap](https://nmap.org/) ·
  [Metasploit](https://www.metasploit.com/) · [Burp Suite](https://portswigger.net/burp) ·
  [VulnHub](https://www.vulnhub.com/) · [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/) ·
  [DVWA](https://github.com/digininja/DVWA)
- **Methodology & standards:** [PTES](http://www.pentest-standard.org/) ·
  [OSSTMM](https://www.isecom.org/OSSTMM.3.pdf) ·
  [NIST 800-53 / RMF](https://csrc.nist.gov/projects/risk-management)

**Authorization is not on the shelf — it's the rule that governs the whole bench:**
only ever point these at systems you own or are explicitly permitted to test.
