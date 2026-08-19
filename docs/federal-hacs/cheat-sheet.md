# GSA HACS orals — cheat sheet

A quick-reference for the federal compliance stack behind the GSA MAS **HACS**
(Highly Adaptive Cybersecurity Services) special item number, **SIN 54151HACS** —
built for anyone studying for the oral technical evaluation, or just learning how the
federal cybersecurity market is bought and run. Everything here is public standards; verify the
current revision before you quote a number (they move).

> **Currency note:** where a standard has a newer revision that changed the
> answer, both are shown — the old one is still widely referenced, the new one is
> what's current. Quoting the retired version is the clearest "studied from an
> old PDF" tell.

---

## Critical numbers (say these without hesitation)

| What | Number |
|---|---|
| HACS service categories | **5** — HVA Assessment, RVA, Pen Testing, Incident Response, Cyber Hunt *(+ the assessment methodologies below)* |
| RMF steps | **7** — Steps 0–6 (NIST 800-37 Rev 2) |
| NIST 800-53 Rev 5 control families | **20** |
| NIST CSF 2.0 functions | **6** — Govern, Identify, Protect, Detect, Respond, Recover (*Govern* added Feb 2024) |
| NIST 800-61 | **r3 (2025)** reorganized IR around the 6 CSF functions; **retired the Rev 2 four-phase lifecycle** |
| MITRE ATT&CK Enterprise tactics | **14** |
| CISA Zero Trust Maturity Model | **v2.0 (2023)** — 5 pillars + 3 cross-cutting capabilities + 4 maturity stages |
| Zero Trust pillars (CISA) | **5** — Identity, Devices, Networks, Applications & Workloads, Data |
| CMMC levels | **3** — L1 = 17 practices, L2 = 110, L3 = 110 + 24 |
| FIPS 199 impact levels | **3** — Low, Moderate, High |
| FedRAMP Moderate timeline | **6–12+ months** |
| EO 14028 incident-reporting window | **72 hours** (federal contractors) |
| CVSS "critical" threshold | **9.0–10.0** |
| Industry attacker dwell time | ~**16–24 days** (varies by annual threat report) |

---

## Answer structure — BLUF (bottom line up front)

A generic oral-eval technique, useful well beyond HACS: **lead with the answer.**

- **Formula:** *[direct answer in one sentence] + [one key fact or number] + [why it matters / a concrete example].*
- Don't open with "So…" or "That's a great question." Open with the answer.

| Question type | Open with |
|---|---|
| "What is X?" | *"X is [definition]. The key thing to know is [one differentiating fact]."* |
| "Difference between X and Y?" | *"X does A, Y does B. The critical distinction is Z."* |
| "Walk me through your approach to…" | *"We follow [framework]. Step one is [first step]…"* |
| "How do you ensure compliance with…?" | *"We treat [standard] as a first-class requirement, not a checkbox — specifically we [concrete thing]."* |
| "Can you give an example?" | *"Yes — [specific system/scenario]: we [specific thing], and the outcome was [result]."* |

---

## The HACS services (SIN 54151HACS)

| Service | One line | Anchor standard |
|---|---|---|
| **HVA Assessment** | CISA-led evaluation of agency High Value Assets | OMB M-19-03 (demand driver) |
| **RVA** — Risk & Vulnerability Assessment | Scanning, config profiling, DB/OS audits → SAR + POA&M | NIST 800-115 |
| **Penetration Testing** | Exploitative control validation under signed rules of engagement | NIST 800-115 · PTES |
| **Incident Response** | Containment, forensics, restoration | NIST 800-61r3 |
| **Cyber Hunt** | Proactive, hypothesis-driven threat hunting for dwell threats | — |

**HVA assessment components** (also offered as methodologies):

- **NAR** — Network Architecture Review: topology, trust boundaries, segmentation gaps.
- **IHEM** — Infrastructure & Hardware Evaluation Methodology: physical/logical infrastructure review.
- **RVA** feeds the same pipeline: scope → scan + interviews → gap analysis → 800-53 mapping → SAR → POA&M.

---

## NIST publications

| Publication | What it is | Key detail |
|---|---|---|
| **800-53 Rev 5** | Federal security control catalog | 20 families, 1,000+ controls; Rev 5 added **SR** (Supply Chain) + **PT** (Privacy) |
| **800-171 Rev 2/3** | CUI protection for non-federal systems | 110 requirements; derived from 800-53 Moderate; feeds CMMC L2 |
| **800-37 Rev 2** | Risk Management Framework (RMF) | 7 steps (0–6) to obtain and maintain an ATO |
| **800-30 Rev 1** | Risk assessment methodology | Threat × Vulnerability × Likelihood × Impact → risk register |
| **800-61r3** | Incident response | 2025; reorganized around CSF 2.0 functions; retired the Rev 2 four-phase lifecycle |
| **800-137** | Continuous monitoring (ISCM) | Required under FISMA; ongoing control assessment |
| **800-161** | Supply chain risk management (SCRM) | Third-party HW/SW risk; aligns with the 800-53 SR family |
| **800-115** | Technical guide to security testing | Federal RVA + pen-test methodology; pair with PTES |
| **800-172** | Enhanced CUI requirements | 24 practices; CMMC L3 source |
| **CSF 2.0** | Cybersecurity Framework | 6 functions (Govern added Feb 2024) |

---

## Laws & mandates

| Document | What it is | Key requirement |
|---|---|---|
| **FISMA** | Federal Information Security Modernization Act | Agencies must run security programs, assess annually, manage a POA&M |
| **EO 14028** | Improving the Nation's Cybersecurity (May 2021) | ZTA adoption, SBOM, **72-hour** incident reporting |
| **OMB M-22-09** | Moving toward Zero Trust | Agencies to reach ZT maturity across 5 pillars |
| **OMB M-19-03** | High Value Asset program (Jan 2019) | Agencies identify HVAs, report to CISA, submit to **CISA-led assessments** — fulfilled via HACS vendors (**direct RVA demand driver**) |

---

## Compliance programs & ATO vocabulary

| Term | Meaning |
|---|---|
| **RMF** | Risk Management Framework (800-37 Rev 2); 7 steps; AO signs the ATO; 3PAO assesses at Steps 4 & 6 |
| **ATO / IATO** | Authorization to Operate (AO accepts residual risk) / Interim ATO (time-limited) |
| **FedRAMP** | Cloud authorization; two paths: **JAB P-ATO** (DHS+DoD+GSA, reusable) or **Agency ATO** (single sponsor) |
| **3PAO** | Third-Party Assessment Organization — FedRAMP-accredited, independent; tests controls, writes the SAR, tracks the POA&M |
| **SSP / SAP / SAR** | System Security Plan (describes controls) / Security Assessment Plan (before testing) / Security Assessment Report (after) |
| **POA&M** | Plan of Action & Milestones — every open finding with control, risk, owner, target date; the AO monitors it continuously |
| **AO / ISSO / ISSM** | Authorizing Official / system-level Security Officer / program-level Security Manager |
| **OSCAL** | NIST machine-readable (JSON/XML) format for SSP/SAR/POA&M; FedRAMP migrating submissions to it |
| **CMMC** | DoD contractor compliance; **C3PAO** assesses L2, **DCSA** (government) assesses L3 |

**CMMC levels**

| Level | Practices | Assessed by | Protects |
|---|---|---|---|
| 1 — Foundational | 17 (FAR 52.204-21) | annual self-assessment | FCI |
| 2 — Advanced | 110 (800-171) | C3PAO | CUI |
| 3 — Expert | 110 + 24 (800-172) | DCSA (government) | highest-risk CUI |

*FCI = Federal Contract Information · CUI = Controlled Unclassified Information.*

**FedRAMP Moderate timeline:** readiness 1–3 mo → 3PAO assessment 3–6 mo → review 2–4 mo = **6–12+ months**.

---

## RMF — the 7 steps

| Step | Name | What happens | Output |
|---|---|---|---|
| 0 | **Prepare** | Org risk strategy; assign AO/ISSO/ISSM; common controls | strategy + roles |
| 1 | **Categorize** | FIPS 199 → Low/Moderate/High (C/I/A impact) | categorization in the SSP |
| 2 | **Select** | 800-53 baseline + overlays | control selection |
| 3 | **Implement** | Apply controls; document how each is met | SSP updated |
| 4 | **Assess** | 3PAO tests controls per the SAP | **SAR + initial POA&M** |
| 5 | **Authorize** | AO reviews SAR + POA&M, accepts residual risk | **ATO** (or IATO, or denial) |
| 6 | **Monitor** | Continuous monitoring per ISCM; POA&M burn-down; reauth triggers | ongoing evidence |

---

## NIST 800-53 Rev 5 — the 20 families

*Know these nine in depth: **AC, AU, CA, CM, IA, IR, RA, SC, SI**.*

| Code | Family | | Code | Family |
|---|---|---|---|---|
| **AC** | Access Control | | **PE** | Physical & Environmental |
| **AT** | Awareness & Training | | **PL** | Planning (SSP is PL-2) |
| **AU** | Audit & Accountability | | **PM** | Program Management |
| **CA** | Assessment, Authorization & Monitoring | | **PS** | Personnel Security |
| **CM** | Configuration Management | | **PT** | PII Processing & Transparency *(Rev 5)* |
| **CP** | Contingency Planning | | **RA** | Risk Assessment |
| **IA** | Identification & Authentication | | **SA** | System & Services Acquisition |
| **IR** | Incident Response | | **SC** | System & Communications Protection |
| **MA** | Maintenance | | **SI** | System & Information Integrity |
| **MP** | Media Protection | | **SR** | Supply Chain Risk Management *(Rev 5)* |

---

## Adversary & threat frameworks

**MITRE ATT&CK — 14 Enterprise tactics (roughly kill-chain order):**
Reconnaissance · Resource Development · Initial Access · Execution · Persistence ·
Privilege Escalation · Defense Evasion · Credential Access · Discovery ·
Lateral Movement · Collection · Command & Control · Exfiltration · Impact.

**STRIDE — threat modeling (each letter attacks one property):**

| Letter | Threat | Property |
|---|---|---|
| **S** | Spoofing | Authentication |
| **T** | Tampering | Integrity |
| **R** | Repudiation | Non-repudiation |
| **I** | Information Disclosure | Confidentiality |
| **D** | Denial of Service | Availability |
| **E** | Elevation of Privilege | Authorization |

**PTES — 7 phases:** Pre-engagement → Intelligence Gathering → Threat Modeling →
Vulnerability Analysis → Exploitation → Post-Exploitation → Reporting.

---

## Zero Trust (CISA ZTMM v2.0)

Five pillars, three cross-cutting capabilities (visibility & analytics; automation
& orchestration; governance), four maturity stages (traditional → initial →
advanced → optimal). Mandated federally by **OMB M-22-09**.

| Pillar | Core question |
|---|---|
| **Identity** | Who is accessing? (MFA, phishing-resistant, no static credentials) |
| **Devices** | What is accessing? (compliance, EDR) |
| **Networks** | How? (segmentation, encryption in transit) |
| **Applications & Workloads** | What are they doing? (authz at the app, WAF, mTLS) |
| **Data** | What can they reach? (encryption, classification, access controls) |

---

## Vulnerability & IR terms

| Term | Meaning |
|---|---|
| **CVSS** | Severity 0–10; Critical = 9.0–10.0 |
| **EPSS** | Probability of exploitation in 30 days (0–1). *CVSS 7.0 + EPSS 0.85 > CVSS 9.0 + EPSS 0.01* — pair them to prioritize |
| **IOC / IOA** | Indicator of Compromise (past, forensic: hashes/IPs/domains) / Indicator of Attack (in-progress, behavioral) |
| **STIG** | DoD hardening guide; CAT I/II/III = Critical/Medium/Low |
| **CVE / NVD** | The vulnerability identifier / NIST's database of CVEs + CVSS |
| **Dwell time** | Compromise → detection; ~16–24 days industry avg |
| **MTTD / MTTR** | Mean Time to Detect / to Respond |
| **RPO / RTO** | Recovery Point Objective (data-loss tolerance) / Recovery Time Objective (downtime tolerance) |
| **ROE / CFAA** | Rules of Engagement (signed **before** any testing) / Computer Fraud and Abuse Act (why the ROE is the legal safe harbor) |

---

## Categorization & crypto

| Standard | What it does |
|---|---|
| **FIPS 199** | Categorizes a system Low/Moderate/High by C/I/A impact → drives the 800-53 baseline |
| **FIPS 200** | Mandates applying the baseline that matches the FIPS 199 categorization |
| **FIPS 140-3** | Cryptographic module validation — which ciphers/key lengths are acceptable |

---

*See [`study-guide.md`](study-guide.md) to understand these rather than memorize
them, and [`flashcards.md`](flashcards.md) for recall practice.*
