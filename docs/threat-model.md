# Threat model — reference platform

**Scope:** the AWS foundation in [`reference-architecture/`](../reference-architecture/) and the
AI components in [`ai-security/`](../ai-security/).
**Method:** [`threat-model-method.md`](threat-model-method.md) — the reusable version of this.
**Last reviewed:** 2026-08-15 · **Owner:** platform security

---

## How to read this if you are not a security engineer

You do not need to understand the mechanisms. Three columns are written for you, and you can skip
the rest:

- **What an attacker gets** — the consequence, in plain terms. No jargon.
- **If it happened, we would have to say** — the sentence that would appear in a customer
  notification or a news story. This is the honest measure of how bad a thing is, and it is
  deliberately uncomfortable to write.
- **Enforced?** — whether the control is actually running, or merely present. These are different,
  and the difference is the point of this repository.

**What this document is asking you for.** Not to be informed — to decide. Every row ends in one of
four states: *mitigated*, *accepted*, *needs a decision*, or *out of scope*. The rows marked **needs
a decision** are the reason this document was sent to you.

**What "residual risk" means.** What is left after the control. No control is perfect, and a threat
model that claims otherwise is selling something.

---

## What we are protecting

Ranked by what it would cost to lose, not by how interesting it is to defend.

| Asset | Why it matters | Worst realistic day |
|---|---|---|
| **Customer documents and their embeddings** | The product's reason to exist. Customers are competitors with each other | One customer reads another's confidential material |
| **Audit records** | The only evidence of what happened. Everything else is reconstruction | An incident occurs and we cannot say what was accessed, or prove it |
| **Deployment credentials** | Control of the platform itself | An attacker changes the running system, including the controls |
| **The control plane** | The thing that enforces every other control | Controls report success while enforcing nothing |

That last row is not a hypothetical. It is a defect class this repository has found in its own code
four times — see [`silent-failure-patterns.md`](silent-failure-patterns.md).

---

## Trust boundaries

A trust boundary is a line where the level of trust changes. Attacks concentrate there, because
that is where an assumption gets made.

![Trust boundaries and attack paths](diagrams/threat-model.svg)

| # | Boundary | The assumption being made |
|---|---|---|
| **B1** | Internet → load balancer | The caller is who they claim to be |
| **B2** | Application → embedding store | The query is scoped to the caller's own tenant |
| **B3** | Model → tool gate | The model's output is a *request*, not a decision |
| **B4** | CI pipeline → AWS | The pipeline is running the code we think it is |
| **B5** | Workload → audit store | Nobody can edit history |

---

## The threats

STRIDE identifiers are in the last column for reviewers who want them. They are not what makes this
document useful, and they are last for that reason.

### T1 · One customer reads another customer's documents

| | |
|---|---|
| **What an attacker gets** | The confidential material of a customer who is not them |
| **If it happened, we would have to say** | *"A customer was able to retrieve documents belonging to another customer. We cannot determine how many were viewed."* |
| **How** | Retrieval scoped by a filter applied *after* the search rather than before, or a query path that forgets the tenant predicate |
| **Control** | Tenant predicate applied **before** ranking, plus a post-condition re-checking every returned row |
| **Enforced?** | ✅ **Verified.** 11 tests, including one that defeats the pre-filter and asserts the guard catches it. Deliberately broken implementations are kept so the tests are provably load-bearing |
| **Residual** | Application-layer enforcement. A direct database query outside the store bypasses it — row-level security in the database would not |
| **Status** | **Mitigated**, residual accepted · STRIDE: Information Disclosure |

> **Why this is first.** It is the only threat here where a single failure is simultaneously a
> contract breach, a notifiable event, and the end of a customer relationship. Nothing else on this
> list ends a business.

### T2 · Content a customer uploads causes the system to act against them

| | |
|---|---|
| **What an attacker gets** | The platform performing privileged actions on the attacker's behalf — sending mail, deleting records, reaching systems |
| **If it happened, we would have to say** | *"Instructions hidden inside an uploaded document caused our system to take actions no user requested."* |
| **How** | Prompt injection. Text inside a retrieved document is read as instruction rather than data, and the model emits a tool call |
| **Control** | Authorization computed from session state established at authentication. No input to that decision is reachable from the prompt, the documents, or the model's output |
| **Enforced?** | ✅ **Verified.** 23 tests, 13-case regression corpus. The harness assumes the model is **already fully compromised** and submits the tool call directly — the worst outcome the injection could achieve |
| **Residual** | Bounded by the tool allowlist. A new tool added without a scope entry is denied by default, which is the intended failure direction |
| **Status** | **Mitigated** · STRIDE: Elevation of Privilege |

> **For non-security readers.** The industry's common answer is to instruct the model to ignore
> suspicious instructions. That is not a control — it fails exactly when it matters, it fails
> silently, and it expires with the next model version. Here the model is *assumed to be
> compromised*, and the protection is ordinary code that the model cannot reach.

### T3 · An attacker edits the record of what they did

| | |
|---|---|
| **What an attacker gets** | Deniability. The incident still happened; the evidence does not |
| **If it happened, we would have to say** | *"We are unable to determine the scope of the incident, because the relevant logs were altered."* |
| **How** | A sufficiently privileged role deletes or rewrites audit objects, or stops the trail |
| **Control** | Object Lock in **COMPLIANCE** mode — not bypassable by any principal, including root, for the retention period. Log-file validation produces digests. The permission boundary denies `StopLogging` and `ScheduleKeyDeletion` |
| **Enforced?** | ✅ **Verified.** Checkov 0 failed with `soft_fail: false`; a custom policy (`CKV_CAC_1`) asserts COMPLIANCE specifically, because built-in checks verify Object Lock is *configured* and not which mode it is in |
| **Residual** | Retention window. Beyond it, records age out by design |
| **Status** | **Mitigated** · STRIDE: Tampering / Repudiation |

### T4 · Anyone who can push a branch can deploy to production

| | |
|---|---|
| **What an attacker gets** | The ability to change the running platform — including turning off the controls on this page |
| **If it happened, we would have to say** | *"An unauthorized change was deployed to production infrastructure."* |
| **How** | The standard CI trust policy wildcards the subject claim — `repo:org/repo:*` — which trusts **every branch, tag and, on many configurations, every fork pull request** |
| **Control** | `StringEquals` against fully-qualified subjects. A variable validation rejects `*` outright, so the wrong value fails at plan time |
| **Enforced?** | ✅ **Verified.** `CKV_CAC_3` fails a wildcarded trust policy; validation blocks the plan |
| **Residual** | Someone with repository admin can add a trusted subject. That is a reviewed Terraform change, not a `git push` — which is the entire point |
| **Status** | **Mitigated** · STRIDE: Spoofing / Elevation of Privilege |

> **The reason this ranks high despite sounding technical.** The credential it exposes has no
> expiry a scanner can see and leaves no artifact to find. Most published examples of this policy
> are written the vulnerable way.

### T5 · Data leaves through a tool the attacker is allowed to use

| | |
|---|---|
| **What an attacker gets** | Data extracted using no privileged capability at all |
| **If it happened, we would have to say** | *"Data was sent to an external destination using a feature working as designed."* |
| **How** | Exfiltration needs a tool that accepts a URL, not a privileged one. A ticket-creation call with a `webhook` parameter is enough |
| **Control** | Destination allowlist on every URL-bearing argument, regardless of the tool's own permission |
| **Enforced?** | ✅ **Verified.** Corpus case `PI-007` uses a tool the session is fully entitled to call |
| **Residual** | An allowlisted host that is itself compromised |
| **Status** | **Mitigated** · STRIDE: Information Disclosure |

### T6 · A control stops working and nothing says so

| | |
|---|---|
| **What an attacker gets** | Time. Every other control on this page becomes optional if the thing enforcing it quietly stops |
| **If it happened, we would have to say** | *"The control was in place, and had not been running for some months."* |
| **How** | A policy set that registers zero checks. A scanner pinned to a version that does not exist. An ignore rule on a path the risk does not travel |
| **Control** | Every gate asserts its own liveness, not just its verdict: policies must **register and fire**, the findings gate must **exit non-zero** against known-bad fixtures, generated artifacts are diffed against their generators |
| **Enforced?** | ✅ **Verified**, and found the hard way — four times, in this repository's own code. [`silent-failure-patterns.md`](silent-failure-patterns.md) |
| **Residual** | Only covers gates someone thought to assert liveness for |
| **Status** | **Mitigated** · STRIDE: Tampering (of the control, not the data) |

> **This is the one worth a manager's attention**, and the least intuitive. A control that reports
> nothing and a control that finds nothing produce identical output: silence. The only way to tell
> them apart is to make each one fail on purpose, on a schedule.

### T7 · A credential reaches the repository and then the cloud

| | |
|---|---|
| **What an attacker gets** | Direct access, using a valid credential, indistinguishable from legitimate use |
| **If it happened, we would have to say** | *"A credential was committed to a repository and used to access customer infrastructure."* |
| **How** | A key committed by accident, or pasted into a fixture, or arriving via a web upload that never consults `.gitignore` |
| **Control** | Layered: `.gitignore` (advisory), a pre-commit hook (skippable), and a CI gate reading `git ls-files` on a machine that is not the author's |
| **Enforced?** | ⚠️ **Partly.** All three run. **GitHub push protection — the only one that blocks a secret *before* it reaches the remote — is not enabled**, because it requires Advanced Security on a private repository. Verified: `422 "Secret scanning is not available for this repository."` |
| **Residual** | **Material.** A credential pushed today is *found*, not *stopped*. It must be treated as exposed and rotated; deleting it in a later commit does not remove it from history |
| **Status** | 🔴 **Needs a decision** — see D1 · STRIDE: Spoofing |

### T8 · The pipeline builds something other than what we reviewed

| | |
|---|---|
| **What an attacker gets** | Code execution inside the pipeline, with the pipeline's access |
| **If it happened, we would have to say** | *"A third-party build component was modified upstream and executed in our pipeline."* |
| **How** | An action pinned to a tag. Tags are mutable — a pin by tag is a promise someone else can rewrite |
| **Control** | Every `uses:` pinned to a 40-character commit SHA, resolved against the API rather than copied |
| **Enforced?** | ⚠️ **Partly.** 16 of 16 pinned by SHA. But this repository shipped an action pinned to a SHA **that did not exist**, and the scan job failed at startup on every run for weeks. Format was correct; function was absent |
| **Residual** | A SHA-pinned action never updates itself, so it ages. Dependabot proposes bumps as reviewable PRs |
| **Status** | **Mitigated**, with a standing requirement to resolve pins rather than trust them · STRIDE: Tampering |

---

## Decisions required

The reason this document exists. Everything above is context for these.

### D1 · Secret push protection is not enabled — accept, or change the plan

**The situation.** GitHub push protection blocks a credential at push time, before it reaches the
remote. It is the only control here that *prevents* rather than *detects*. It requires Advanced
Security on a private repository, and is **free on public ones**.

**Plain-language consequence of doing nothing:** a credential committed by accident is discovered
after it is already on GitHub's servers. It must be treated as exposed and rotated, and it stays in
history until the history is rewritten.

| Option | Cost | Residual |
|---|---|---|
| **Enable on publication** | £0 — free once public | Gap persists until then. **Recommended** |
| Purchase Advanced Security | Per-committer licence | Closed now |
| Accept as-is | £0 | Detection only, indefinitely |

**Decision needed from:** repository owner. **By:** before any credential-bearing work.

### D2 · Application-layer tenant isolation, or database-enforced

**The situation.** Tenant isolation is enforced in application code. It is tested and it holds. But
a query written outside that path — a migration, an admin script, a reporting job — is not subject
to it. PostgreSQL row-level security would enforce below the ORM, where a forgotten `WHERE` clause
cannot bypass it.

**Plain-language consequence of doing nothing:** the strongest protection on the most valuable asset
depends on every future developer remembering something.

| Option | Cost | Residual |
|---|---|---|
| Keep application-layer | £0 | Depends on discipline in code not yet written |
| Add RLS as defence in depth | Days of work, some query overhead | Bypass requires database privilege. **Recommended** |

**Decision needed from:** engineering lead. **By:** before the first admin or reporting path is
written.

---

## Out of scope, deliberately

Saying what a document does *not* cover is what stops it being read as a clean bill of health.

| Not covered | Why |
|---|---|
| Physical and datacentre security | Inherited from the cloud provider; assessed via their attestations |
| Denial of service | Availability is modelled separately; this document is about confidentiality and integrity |
| Insider threat by the repository owner | Single-author repository. `enforce_admins` is false and the owner can bypass every rule — a real limitation, stated rather than implied |
| Social engineering of staff | Personnel control, not a platform control |
| Anything about a real production environment | This models the reference implementation. It is written from public standards against synthetic targets |

---

## How this document stays true

A threat model reviewed once is a snapshot, and a snapshot is wrong within a quarter.

- **Re-reviewed** when a trust boundary moves — a new ingress, a new data store, a new tool the model
  can call. Not on a calendar.
- **The "Enforced?" column is checkable.** Every ✅ points at a test or a gate that runs in CI. If
  the claim and the pipeline disagree, the pipeline is right.
- **A prompt injection that worked once becomes a permanent test case**, not a ticket. Filed as a
  ticket it gets fixed and forgotten; added to the corpus it fails the build the day it returns.
