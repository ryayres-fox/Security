# GSA HACS orals — study guide

The [cheat sheet](cheat-sheet.md) is for recall. This is for **understanding** —
so that when a question comes in a shape you didn't rehearse, you can reason to
the answer instead of reaching for a memorized one. Public standards throughout.

---

## The frame: what HACS is, and why it's bought

**GSA MAS** (Multiple Award Schedule) is the government's pre-approved contract
vehicle for commercial services. A **SIN** (Special Item Number) is a category
within it; **54151HACS** is Highly Adaptive Cybersecurity Services. Winning it
means an agency can buy your cybersecurity services quickly, without a fresh
full procurement each time.

The **demand driver** to internalize: **OMB M-19-03** requires agencies to
identify their High Value Assets and submit to **CISA-led assessments** — and
CISA fulfills many of those through HACS vendors. So the HVA/RVA work isn't
speculative; it's a standing federal mandate looking for qualified performers.

---

## The five services, explained

- **HVA Assessment.** A CISA-led evaluation of a system whose compromise would
  cause severe national, economic, or public-health impact. Two named components
  you'll be asked about: **NAR** (Network Architecture Review — topology, trust
  boundaries, segmentation gaps) and **IHEM** (Infrastructure & Hardware
  Evaluation Methodology — the physical/logical infrastructure review).
- **RVA — Risk & Vulnerability Assessment.** The broad one: scanning,
  configuration profiling, database and OS audits, interviews. The *flow* is the
  answer: scope → scan + interview → gap analysis → map findings to **800-53**
  controls → **SAR** → **POA&M**. Methodology anchor: **NIST 800-115**.
- **Penetration Testing.** Exploitative validation — proving a control fails, not
  just noting it might. The non-negotiable is the **ROE** (Rules of Engagement),
  signed *before* any testing. Without it, unauthorized access is a **CFAA**
  crime; the ROE is the legal safe harbor. Methodology: **800-115** + **PTES**.
- **Incident Response.** Containment, forensic acquisition, eradication,
  restoration. The anchor moved: **NIST 800-61r3 (2025)** reorganized IR around
  the **CSF 2.0 functions** and retired the Rev 2 four-phase lifecycle. Know both
  — Rev 2's *Preparation → Detection/Analysis → Containment-Eradication-Recovery
  → Post-Incident* is still widely referenced, but r3 is current, and quoting only
  r2 dates you.
- **Cyber Hunt.** Proactive, hypothesis-driven hunting for adversaries that
  automated tools miss — aimed squarely at **dwell time** (compromise-to-detection,
  ~16–24 days industry average).

---

## RMF — reason about it, don't recite it

The Risk Management Framework (**800-37 Rev 2**) is the seven-step path to an
**ATO**. The logic connects the steps:

1. **Prepare** — set the risk strategy and the roles (AO, ISSO, ISSM).
2. **Categorize** — **FIPS 199** rates the system Low/Moderate/High on
   confidentiality, integrity, availability. *This number drives everything after
   it.*
3. **Select** — pick the **800-53** baseline matching that categorization
   (**FIPS 200** makes applying it mandatory).
4. **Implement** — build the controls; write down how each is met (in the SSP).
5. **Assess** — an independent **3PAO** tests them and produces the **SAR** and
   the initial **POA&M**.
6. **Authorize** — the **AO** reads the SAR + POA&M and *accepts the residual
   risk* by signing the **ATO**. (Authorization is a risk decision, not a
   certificate.)
7. **Monitor** — continuous monitoring (**ISCM**, 800-137); the POA&M is burned
   down; big changes trigger reauthorization.

The one-sentence version: *"RMF categorizes the system, selects and implements
controls to match, has them independently assessed, and puts a named official on
the hook to accept whatever risk remains — then watches it continuously."*

---

## FedRAMP and the 3PAO — where independence earns its keep

**FedRAMP** authorizes cloud services for federal use. Two paths:

- **JAB P-ATO** — the Joint Authorization Board (DHS + DoD + GSA) issues a
  *provisional* ATO that any agency can reuse. Highest scrutiny.
- **Agency ATO** — a single agency's AO authorizes it; other agencies can reuse
  the package but make their own decision.

The **3PAO** is the load-bearing piece: an accredited, *independent* assessor that
tests the controls, writes the SAR, and tracks the POA&M. Independence is the
whole point — an agency AO trusts the package because the people who tested it
don't work for the vendor who built it. (This is the same principle as any
security control: *the assessment is only worth what its independence is worth.*)

**Timeline reality:** FedRAMP Moderate runs **6–12+ months**. Say the number
plainly; pretending it's fast reads as inexperience.

---

## CMMC — three levels, three assessors

Defense-contractor compliance, tiered by data sensitivity:

- **L1 (Foundational)** — 17 practices from FAR 52.204-21, protecting **FCI**
  (Federal Contract Information); **annual self-assessment**.
- **L2 (Advanced)** — the 110 requirements of **800-171**, protecting **CUI**
  (Controlled Unclassified Information); assessed by a **C3PAO**.
- **L3 (Expert)** — L2 plus 24 enhanced practices from **800-172**, for the
  highest-risk programs; assessed by **DCSA** (the government itself).

The pattern to remember: *as the data gets more sensitive, the assessor gets more
independent* — self → third party → government.

---

## Zero Trust — what it actually removes

Zero Trust removes **implicit trust from the network**: no request is trusted
because of where it came from; every one is verified. The current federal
reference is the **CISA Zero Trust Maturity Model v2.0 (2023)** — five pillars
(Identity, Devices, Networks, Applications & Workloads, Data), three cross-cutting
capabilities (visibility & analytics, automation & orchestration, governance), and
four maturity stages. **OMB M-22-09** is the mandate. Quoting a "five-pillar"
graphic without the cross-cutting layer and maturity stages reads as v1-era.

---

## Prioritization — the one that separates practitioners

Anyone can quote **CVSS** (severity, 0–10). The practitioner move is pairing it
with **EPSS** (probability of exploitation in the next 30 days): *a CVSS 7.0 with
EPSS 0.85 is more urgent than a CVSS 9.0 with EPSS 0.01.* Severity is how bad it
would be; EPSS is how likely it is to happen. You patch the intersection first.

---

## Delivering it: the oral itself

The content gets you in the room; delivery wins it. This is transferable to any
technical oral or panel:

- **Lead with the answer (BLUF).** Direct answer → one number or distinction →
  why it matters. Never open with "So…" or "great question."
- **Name the standard, then the step.** "We follow 800-115. Step one is scoping
  and the ROE." Specificity reads as experience.
- **Separate "we have a control" from "the control is running."** Almost no one
  does, and it's the most credible thing you can say — evidence over assertion.
- **Give the number, including the uncomfortable one.** "FedRAMP Moderate is
  6–12 months." Honesty about cost and timeline builds more trust than optimism.
- **If you don't know, say the boundary.** "That's outside what I've done
  directly; here's how I'd approach it." A named gap beats a bluff every time.

---

*Recall practice: [`flashcards.md`](flashcards.md). Quick reference:
[`cheat-sheet.md`](cheat-sheet.md).*
