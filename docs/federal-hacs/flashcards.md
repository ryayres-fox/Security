# GSA HACS orals — flashcards

**How to use:** cover the answer, read the question, say it out loud, then check.
Aim for under 30 seconds on an acronym, under 60 on a concept. Work one deck at a
time. Public standards throughout — verify the current revision before you rely
on a number.

---

## Deck 1 — Contract & vehicle

**Q: What is GSA MAS?**
A: General Services Administration Multiple Award Schedule — the government's pre-approved contract vehicle for commercial products and services.

**Q: What is a SIN, and which one is HACS?**
A: Special Item Number — a service category within a MAS contract. HACS is **54151HACS**.

**Q: What does HACS stand for?**
A: Highly Adaptive Cybersecurity Services.

**Q: Name the five HACS services.**
A: HVA Assessment, RVA (Risk & Vulnerability Assessment), Penetration Testing, Incident Response, Cyber Hunt.

**Q: SOW vs PWS?**
A: A Statement of Work defines specific tasks and deliverables; a Performance Work Statement is outcome-based — what the result should be, not how to do it.

---

## Deck 2 — Frameworks & standards

**Q: What is RMF and where is it defined?**
A: The Risk Management Framework — NIST 800-37 Rev 2 — a 7-step process (0–6) to obtain and maintain an ATO.

**Q: Name the 7 RMF steps.**
A: Prepare, Categorize, Select, Implement, Assess, Authorize, Monitor.

**Q: How many 800-53 Rev 5 control families, and what two did Rev 5 add?**
A: 20 families. Rev 5 added **SR** (Supply Chain Risk Management) and **PT** (PII Processing & Transparency).

**Q: What changed for incident response in NIST 800-61r3 (2025)?**
A: It reorganized IR around the CSF 2.0 functions and retired the Rev 2 four-phase lifecycle (Preparation → Detection/Analysis → Containment-Eradication-Recovery → Post-Incident).

**Q: What are the six NIST CSF 2.0 functions, and which is new?**
A: Govern, Identify, Protect, Detect, Respond, Recover. **Govern** was added in Feb 2024.

**Q: What does FIPS 199 do, and how does it connect to 800-53?**
A: It categorizes a system Low/Moderate/High on confidentiality, integrity, availability — which drives the 800-53 baseline you select. FIPS 200 makes applying that baseline mandatory.

**Q: What is 800-115 used for?**
A: The federal technical guide to security testing — the methodology anchor for both RVA and penetration testing.

---

## Deck 3 — ATO & compliance programs

**Q: SSP vs SAP vs SAR?**
A: System Security Plan (describes the system and how each control is met), Security Assessment Plan (written before testing — scope and method), Security Assessment Report (the results, after testing).

**Q: What is a POA&M?**
A: Plan of Action & Milestones — every open finding with its control, risk level, owner, and target remediation date. The AO monitors it continuously.

**Q: Who signs the ATO, and what are they actually doing?**
A: The Authorizing Official — accepting the residual risk. Authorization is a risk decision, not a certificate.

**Q: What are FedRAMP's two authorization paths?**
A: JAB P-ATO (Joint Authorization Board — DHS+DoD+GSA — reusable by any agency) and Agency ATO (a single agency's AO, package reusable).

**Q: What does a 3PAO do, and why does independence matter?**
A: An accredited, independent assessor tests controls, writes the SAR, and tracks the POA&M. Independence is what makes an agency AO trust the package — the testers don't work for the vendor.

**Q: What is OSCAL?**
A: NIST's machine-readable (JSON/XML) format for SSPs, SARs, and POA&Ms. FedRAMP is migrating submissions to it, replacing Word documents.

**Q: The three CMMC levels — practices and assessor?**
A: L1 = 17 practices, annual self-assessment (FCI). L2 = 110 (800-171), C3PAO (CUI). L3 = 110 + 24 (800-172), DCSA/government (highest-risk CUI).

---

## Deck 4 — Laws & mandates

**Q: FISMA vs FedRAMP?**
A: FISMA is the law requiring agencies to secure their systems; FedRAMP certifies cloud vendors so agencies can meet that obligation efficiently.

**Q: What did EO 14028 require?**
A: Zero-trust adoption, SBOMs for software, and a **72-hour** incident-reporting window for federal contractors.

**Q: What is OMB M-19-03, and why does it matter to HACS?**
A: The High Value Asset program — agencies identify HVAs and submit to CISA-led assessments, which CISA fulfills through HACS vendors. It's the direct demand driver for RVA work.

**Q: What is OMB M-22-09?**
A: The federal Zero Trust mandate — agencies must reach ZT maturity across the five CISA pillars.

---

## Deck 5 — Adversary & prioritization

**Q: How many MITRE ATT&CK Enterprise tactics, and what's the first and last?**
A: 14 — starting with Reconnaissance and ending with Impact.

**Q: Spell out STRIDE and the property each attacks.**
A: Spoofing (authentication), Tampering (integrity), Repudiation (non-repudiation), Information Disclosure (confidentiality), Denial of Service (availability), Elevation of Privilege (authorization).

**Q: CVSS vs EPSS — and how do you use them together?**
A: CVSS scores severity (0–10); EPSS predicts exploitation probability in 30 days (0–1). Prioritize the intersection — a CVSS 7.0 with EPSS 0.85 outranks a CVSS 9.0 with EPSS 0.01.

**Q: IOC vs IOA?**
A: Indicator of Compromise — forensic evidence of a past attack (hashes, IPs, domains). Indicator of Attack — behavioral evidence of an attack in progress.

**Q: Why must the ROE be signed before a pen test?**
A: Unauthorized computer access is a crime under the CFAA; the signed Rules of Engagement are the legal safe harbor.

**Q: RPO vs RTO?**
A: Recovery Point Objective — how much data you can afford to lose (drives backup frequency). Recovery Time Objective — how fast you must restore (drives redundancy).

---

*Understand the "why" behind these in [`study-guide.md`](study-guide.md); the
one-page reference is [`cheat-sheet.md`](cheat-sheet.md).*
