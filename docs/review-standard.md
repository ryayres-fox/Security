# Review standard

How changes to this repository get reviewed, and why the bar sits where it does.

This is written for a repository whose entire argument is that controls should be
*enforced and provable* rather than documented. A review process that does not
hold itself to that is the first counter-example, so this document is also a
control, and it is meant to be used against the person who wrote it.

---

## 1. The posture

**The default verdict is BLOCKED.** A change does not start approved and lose
it. It starts blocked and earns its way out by producing evidence. "I read it
and found nothing wrong" is not a passing review — it is an unfinished one.

**Absence of evidence is itself a finding.** If a change asserts that something
was tested, deployed, verified or is safe, and there is no output, no command,
no run link behind it, that is a finding with a severity — not a question, not a
"could you confirm". The burden of proof sits on the change, never on the
reviewer.

**Unverifiable is worse than wrong.** A wrong claim can be corrected. A claim
that cannot be checked from what was provided means the change is not reviewable,
and an unreviewable change is blocked on process grounds no matter how good the
code looks.

**Nobody gets the benefit of the doubt, including the reviewer's own earlier
conclusion.** Not a passing CI check, not a comment in the code, not a prior
approval. Verify it, or write down that you didn't.

**Severity is not a negotiation.** Nothing gets talked down because a deadline is
close or because the fix is large. Those are real considerations and they belong
in an explicit, dated risk acceptance — never in the severity column.

**No soft language in findings.** "Consider", "might want to", "nit", "not a
blocker but" are all ways of raising a problem while pre-forgiving it. If it is
worth writing down it gets a severity. If it does not deserve one, delete it
rather than laundering it into the review as advice.

**Be exacting about the artifact and neutral about the person.** *"This returns
500 on every upload — here is the command and the output"* is unarguable.
*"This is sloppy"* invites an argument evidence cannot settle. Ruthless on the
work, immovable on the standard, neutral about the human.

**Self-review does not lower the bar; it raises it.** Most of the defects worth
recording in this repository were found in its own work by refusing to extend
itself the benefit of the doubt. See §6.

---

## 2. Severity

| | Definition | Merge impact |
|---|---|---|
| 🔴 **Critical** | Credential exposure, broken authorization, a control that is asserted somewhere but **does not exist in the running system**, or a change deployed before review | **Blocks.** Cleared by a fix or a written, dated risk acceptance. Never by discussion |
| 🟠 **High** | Significant weakness, broken logic with measurable impact, **any claim that cannot be verified from what was provided** | **Blocks.** Same two exits |
| 🟡 **Medium** | Overly broad permissions, missing validation on non-critical input, undocumented breaking change | Does not block, but needs a filed issue **linked before merge**. "Will file later" is an untracked defect, and it gets re-raised as High |
| 🔵 **Low** | Modernization, style, missing non-critical docs | Backlog |
| ⚫ **Info** | Observation or question with no clear right answer | Discussion |

Three rules that are not open to interpretation:

- **High blocks.** Anything softer than that means it does not.
- **Unverified defaults to High**, not Medium. The reviewer does not absorb the
  cost of missing evidence.
- **Blast radius raises severity by one level.** The same defect in a shared
  module, a CI gate, or anything on an audit path is worse than in a
  self-contained tool. Say which applies and why.

---

## 3. The Verification Ledger

Every review records what was **executed**, not what was read.

| # | Command | Result | What it proves |
|---|---|---|---|
| 1 | `pytest … -q` full, no suppression flags | `98 passed` | baseline held; nothing silently excluded |
| 2 | `checkov -d reference-architecture/` | `114 / 0 / 10` | every skip is inline and reasoned |

Rules:

- **No suppression flags, ever.** `-k`, `--ignore`, `--deselect`, `|| true`,
  `continue-on-error` in the verification path invalidate the result. A test
  collection error is a finding, not something to step around — and reporting
  "N passed" when M tests were silently excluded is a false green.
- **Record the collected count, not just the pass count.** 307 → 285 passing is
  a regression even when all 285 are green.
- **"CI is green" is not a ledger row** unless you confirmed the specific job
  actually covers the changed code. A job can pass by not running.
- **Say what you could not run, and why.** That goes in Assumptions and it caps
  how much the verdict is allowed to claim.

---

## 4. What gets checked, by area

### 4.1 Any change

- Every claim in the description has a ledger row behind it.
- New behaviour has a test that **fails when the behaviour is removed**. A test
  that passes against both the fixed and the broken implementation proves
  nothing. Where practical, demonstrate it — this repository keeps deliberately
  broken implementations (`LeakyStore`, `StarvedStore`) precisely so the tests
  that distinguish them are provably load-bearing.
- No secret, credential, account ID, ARN, internal hostname or real domain
  anywhere in the diff, **fixtures included**.
- No machine-local path, scratchpad path, or chat/artifact URL in the diff, the
  commit messages, or the PR body. Every reference must resolve for a reader who
  is not you.

### 4.2 Terraform

- `fmt -check` and `validate` clean, on **every** module directory rather than
  the one that happened to be wired into CI.
- `checkov` 0 failed. Suppressions are inline at the resource with a written
  reason and mirrored into `controls.yaml`. **`soft_fail` is never acceptable** —
  it makes everything pass and therefore means nothing.
- Constraints belong in `validation` blocks, not in comments. A comment saying
  "don't use a wildcard here" is advice, and advice does not survive a deadline.
- Every service-principal grant carries a source condition. A policy that trusts
  a service without one is usable by any account — the confused-deputy path, and
  the default shape of most published examples.
- No `Resource = "*"` or `Action = "*"` without a written reason that explains
  why a scoped form cannot express the control.

### 4.3 Controls and mapping

- Every control claimed has an `evidence` field naming what proves it. "We
  implement AU-9" is an assertion; "log file validation is enabled and here is
  the assertion" is a control.
- `tools/control_coverage.py --check` passes, and the committed coverage report
  matches a freshly generated one.
- A control is described as **implemented and enforced**, never as *satisfied*.
  Satisfaction is an assessor's judgment involving policy and scope that live
  outside a repository, and conflating them is how organizations get surprised.

### 4.4 CI and workflows

- Every `uses:` pinned to a 40-character SHA **that was resolved against the
  API**, not to a tag and not to a plausible-looking SHA. Prefer the SHA of a
  specific patch release over a major-version alias: an alias is a pin someone
  else can re-point.
- Every `pip install` in a `run:` block pins an exact version. An unpinned lint
  tool means CI and local silently enforce different rules.
- `timeout-minutes` on every job. Top-level `permissions:` declared.
- A gate must be **watched failing at least once**. A gate nobody has seen fail
  is a gate nobody knows works — which is why `normalizer-gate` asserts a
  non-zero exit rather than a zero one.

### 4.5 Findings pipeline (`findings-normalizer/`)

- Identity must survive a re-scan. Nothing volatile — line numbers, timestamps,
  remediation prose — may enter the identity hash.
- Where two tools share an upstream rule database, identity uses the **shared**
  identifier, not either vendor's friendly name.
- A new parser ships a fixture in `samples/`. A parser with no fixture is a
  parser nobody has run, and a registry test enforces this.
- A parser must never copy secret material out of a scanner's output into the
  normalized record. The tool that finds a leak must not become the tool that
  spreads it.
- Tolerate the input shape the tool actually emits, including the awkward one.
  Handling only the common shape returns zero findings and a green build, which
  is a silent fail-open.

### 4.6 AI-facing code (`ai-security/`)

- Assume the model is **already fully compromised** by content it retrieved.
  Then ask what still holds. Anything that depends on the model declining to
  comply is not a control.
- No authorization input may be reachable from a prompt, a retrieved document,
  or model output. Scopes come from the session, established by authentication.
- Tenant predicates apply **before** ranking, not after. Post-filtering isolates
  and starves, and it passes a naive isolation test while doing so.
- Model output selects from a typed, parameterized allowlist — never a free-form
  command string.
- Irreversible actions require a confirmation bound to the exact arguments a
  human approved. An unbound token turns a confirmation dialog into a rubber
  stamp.
- No test asserts on generated text. A test whose expected output is
  model-generated gets quarantined the first time it flakes, and quarantined
  tests defend nothing.

---

## 5. Verdict format

```
VERDICT: [ APPROVED | APPROVED WITH COMMENTS | CHANGES REQUESTED | BLOCKED ]

Blocking (must fix before merge):
  - R-001: <one line>

Non-blocking (fix here, or file an issue and link it before merge):
  - R-002: <one line>

Backlog:
  - R-003: <one line>
```

Findings table: `ID | Severity | Category | File | Line | Issue | Required action`.
Assumptions table: `ID | Detail`. State `None` if there are none — an empty
section reads as "not considered".

---

## 6. Worked example — the finding this standard exists for

The repository's CI declared an infrastructure-scanning gate with
`soft_fail: false`, and pinned the scanning action to a 40-character SHA. It
looked exactly like the practice this repository argues for: pinned by digest,
failing closed, reviewed.

The SHA did not exist.

```
GET /repos/<action>/commits/99bb2caf247dfd9dfd22e0a6f6dcc16ea99e0c60
422  "No commit found for SHA"
```

GitHub resolves a `uses:` reference before the job starts, so the scan job
failed at startup on every run. The IaC gate had **never executed**. Every other
signal said the control was in place: it was in the config, it was pinned
correctly by format, and nothing was reported against it — because nothing ran.

Three things generalise from it, and they are the reason for §1 and §3:

1. **A control that reports nothing looks identical to a control that finds
   nothing.** Silence is not evidence. The only way to tell them apart is to
   watch the thing fail on purpose.
2. **Correct form is not correct function.** The pin had the right shape. Format
   checks — 40 hex characters, comment naming the version — all passed. Only
   resolving it against the API found the defect.
3. **Verifying the enforcement path is a different activity from reading the
   diff**, and only the first one would have caught this.

It was found by reviewing this repository against this standard, in its own
work, before anyone else saw it. That is the intended use.
