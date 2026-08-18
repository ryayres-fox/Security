# Software & vendor security review — an intake template

Most incidents don't come through the front door you're watching. They come
through something a team *brought in* — a SaaS app, a browser extension, an
integration, a vendor holding a token into your environment — that nobody
reviewed, because there was no cheap way to ask the right questions.

This is that cheap way: a template anyone can copy and fill out **before**
adoption. A short, honest intake beats a 200-question spreadsheet nobody
completes. The goal is a **decision you can defend**, not a compliance ritual.

**How to use it.** The requester fills **Part A**. Security fills **Part B** and
records a decision with an owner and a re-review date. If a field is "don't
know," *write "don't know"* — an unanswered question is a finding, not a blank.

---

## Part A — the requester fills this

### 1 · What is it, and what does it do?

- **Name / vendor / URL:** `____`
- **What it does, in one line:** `____`
- **Who is requesting it, and the business need:** `____`
- **Who will own it internally once it's live:** `____`

### 2 · Is it maintained and viable?

- **Actively maintained?** (last release, release cadence) `____`
- **Open source or commercial?** — if OSS: contributors / bus-factor; if
  commercial: company size, how long in business `____`
- **End-of-life or support status:** `____`

> *Why it matters:* an abandoned tool stops getting security fixes, and you
> inherit its unpatched CVEs as your own.

### 3 · Is it certified / compliant?

- **Attestations held:** SOC 2 Type II · ISO 27001 · FedRAMP · HIPAA · PCI-DSS ·
  other → `____`
- **Can they provide the actual report/attestation** (not just a logo on a
  marketing page)? `____`
- **Where is it hosted / data residency:** `____`
- **Sub-processors / fourth parties it relies on:** `____`

> *Why it matters:* a certification you can't obtain the report for is a
> marketing claim, not evidence.

### 4 · What permissions / access does it require?

- **Permissions or OAuth scopes requested:** `____`
- **Does it need admin, or can it run least-privilege?** `____`
- **Does it act on our behalf** — hold a token, a webhook, or a key into our
  systems? `____`
- **Human access model:** SSO / SAML / OIDC? · MFA enforced? · role-based? `____`

> *Why it matters:* the blast radius of a compromise is exactly what you granted
> it — no more, no less.

### 5 · What data does it need, and how does it store it?

- **Data it touches, by classification:** public · internal · confidential ·
  **regulated** (PII / PHI / PCI / other) → `____`
- **Volume and sensitivity:** `____`
- **Does data leave our environment?** (yes / no; if yes, to where) `____`
- **Where and how is it stored:** encrypted at rest? · encrypted in transit
  (TLS)? · **who holds the keys?** `____`
- **Retention and deletion:** how long, and what happens to our data when we
  offboard? `____`

> *Why it matters:* one leaked regulated dataset can end a contract. This section
> sets the whole risk tier — answer it before anything else.

### 6 · How is it accessed and secured — in your environment, or in ours?

- **Deployment model:** SaaS (their cloud) · self-hosted (our cloud) · on-prem ·
  agent on endpoints → `____`
- **Network exposure:** internet-facing? · behind SSO / VPN? · does it open
  inbound connections *to us*? `____`
- **In *their* environment** — what secures it, and how do we verify (attestation,
  pen-test summary)? `____`
- **In *our* environment** — segmentation, egress controls, logging / monitoring,
  how secrets for it are stored: `____`
- **Who administers it, and how is that admin access controlled?** `____`

> *Why it matters:* "secured" means different things on their box versus ours.
> Name which side owns each control — the gaps are the hand-offs nobody claimed.

### 7 · What happens when it goes wrong?

- **If it's breached, what's our exposure, and can we cut it off quickly?** `____`
- **Data export / portability if we leave:** `____`
- **Contractual security terms:** DPA · BAA · breach-notification SLA · right to
  audit → `____`

---

## Part B — security fills this

- **Data risk tier:** low · moderate · high · regulated
- **Findings** (evidence, not assertion): `____`
- **Required controls / conditions before use:** `____`
- **Decision:** ✅ approved · ⚠️ approved with conditions · ⏸️ deferred (with a
  dated plan) · ⛔ rejected
- **Owner and expiry — when does this get re-reviewed:** `____`

A decision that isn't written down, with an owner and a date, is not a decision —
it's a thing someone will later assume was approved. This mirrors how a code
review hold clears in [`review-standard.md`](review-standard.md): **fixed, or
accepted in writing with an owner and an expiry — there is no third path.**

---

## Using it well

- **Right-size the review to the data tier.** A read-only tool touching public
  data is a five-minute yes; a vendor holding *regulated* data with a token into
  production earns every question here.
- **Evidence over assertion.** "We're SOC 2" is a claim; the report is evidence.
  "It's encrypted" is a claim; *who holds the key* is the control.
- **A blank is a finding.** "Don't know" is a legitimate answer that creates a
  follow-up — never a reason to skip the row.
- **Re-review on a clock.** Certifications lapse, vendors get acquired, scopes
  creep. Approval with no expiry is approval *forever*.

Publish this so teams can self-serve the intake, and so a rejection is never a
surprise — the same reason [`review-standard.md`](review-standard.md) exists for
code changes. This one is for everything you *bring in*.
