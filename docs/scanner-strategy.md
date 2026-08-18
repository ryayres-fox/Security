# Choosing security scanners — what each one is for, and when not to use it

This repository runs seven scanners. Listing them without explaining any of it is
the norm, and it is useless to anyone deciding what *they* should run.

**Written for someone who has not done this before.** Every term is defined the
first time it appears. If you already know what SAST is, skim the first section.

---

## First: the categories, not the tools

Tool names change. The categories do not. Each answers a different question, and
most confusion about "why do we have five scanners" comes from not noticing that.

| Category | The question it answers | When it can possibly run |
| --- | --- | --- |
| **Secrets scanning** | *Did someone commit a password, key or token?* | The moment code exists |
| **SAST** — Static Application Security Testing | *Does this source code contain a dangerous pattern?* | Any time you have source |
| **IaC scanning** — Infrastructure as Code | *Would this infrastructure definition create something insecure?* | Before you deploy it |
| **SCA** — Software Composition Analysis | *Do the libraries we depend on have known vulnerabilities?* | Once dependencies are resolved |
| **Container scanning** | *Does the built image contain vulnerable packages?* | After the image is built |
| **CSPM** — Cloud Security Posture Management | *Is what is actually running configured badly?* | Only after deployment |
| **DAST** — Dynamic Application Security Testing | *Can I break the running application from outside?* | Only against something running |

Two things fall out of that table immediately.

**They are not alternatives.** They look at different artifacts at different
times. Asking "should we use SAST or CSPM" is like asking whether to use a
spell-checker or a proofreader.

**Only one of them sees reality.** Everything except CSPM and DAST examines a
*description* of the system. Infrastructure code says what you asked for; CSPM
says what you got. Those differ more often than anyone is comfortable with.

---

## The seven tools here

| Tool | Category | Looks at | Runs at |
| --- | --- | --- | --- |
| **Gitleaks** | Secrets | Git history and working tree | Pre-commit, and in CI |
| **Semgrep** | SAST | Source code, any language | Pull request |
| **Bandit** | SAST | Python source only | Pull request |
| **Checkov** | IaC | Terraform, CloudFormation, Kubernetes | Pull request, before deploy |
| **tfsec** | IaC | Terraform | Pull request, before deploy |
| **Trivy** | Container + SCA + IaC | Images, dependency manifests, IaC | Build |
| **ASFF** | CSPM (format) | Findings from AWS Security Hub | Continuously, post-deploy |

**ASFF is not a scanner.** It is the AWS Security Finding Format — the JSON
shape that AWS Security Hub emits when GuardDuty, Inspector, Config and others
report. The repo has an ASFF *parser* so cloud findings land in the same store as
everything else. Worth stating plainly, because "asff" in a tool list looks like
a scanner and is not.

---

## Sequencing, and why the order is not arbitrary

![Scanner sequencing](diagrams/scanner-sequence.svg)

The order follows one rule: **catch each class of problem at the earliest point
it can possibly be detected**, because the cost of fixing rises at every stage.

### 1 — Secrets, first, always

Gitleaks runs before anything else, ideally before the commit exists.

A leaked credential is the only finding that is **already an incident**. Every
other scanner reports something that *might* be exploited later; a committed key
is exposed the instant it is pushed, and rotating it is mandatory regardless of
what you do to the code.

It also runs fastest, so there is no argument for putting it later.

> **The limit nobody mentions:** deleting a secret in a later commit does not
> remove it. It stays in history. Gitleaks scanning history is what catches
> that — and it is why *push protection*, which blocks the secret before it
> reaches the server, is stronger than any scanner. See
> [`../SECURITY.md`](../SECURITY.md).

### 2 — SAST and IaC, at pull request

Both examine source, so both can run the moment a change is proposed. This is
the cheapest place to fix anything: the author still has the context, and nothing
has been deployed.

IaC scanning specifically belongs **before `terraform apply`**. A misconfiguration
caught at plan time is a text edit. The same misconfiguration caught after
deployment is a change-managed fix against something with traffic on it.

### 3 — Container and dependency scanning, at build

These need artifacts that do not exist until the build runs — a resolved
dependency tree, a built image.

### 4 — CSPM, continuously, after deploy

The only category that sees what is really there. It catches drift (someone
changed it in the console), things created outside your IaC, and anything your
IaC scanner had no rule for.

It is also the slowest feedback loop, which is exactly why the earlier stages
exist.

---

## Why run overlapping tools

Checkov, tfsec and Trivy all scan Terraform. That looks redundant and mostly is
not.

- **Different rule databases.** Each vendor writes rules for what its customers
  hit. Coverage overlaps but is not identical.
- **Agreement across tools is signal.** Two independent scanners flagging the
  same resource is stronger evidence than one. The normalizer records every tool
  that reported a finding for exactly this reason.
- **Redundancy survives a tool dying.** tfsec has effectively merged into Trivy
  upstream — a repo that only ran tfsec would slowly stop being scanned.

**The cost is triage noise**, and that cost is real. Three tools reporting the
same misconfiguration three times is how a backlog becomes unreadable. That is
the entire reason [`../findings-normalizer/`](../findings-normalizer/) exists:
deduplicate across tools, keep every attribution.

**If you have no way to deduplicate, run fewer scanners.** Overlap without
normalization is worse than a single tool.

---

## When *not* to use each one

The half that usually goes unwritten. None of these is a reason to avoid the
tool; they are the conditions under which it will waste your time.

### Gitleaks
- **It finds what was committed, not what is live.** It cannot tell a rotated key
  from an active one. Every hit needs a human to check.
- **Entropy-based rules produce false positives** — test fixtures, base64 blobs,
  UUIDs. Budget for tuning or people will start ignoring it.
- **It does not see secrets that were never committed** — environment variables,
  CI variables, a vault. That is most of them, and it is a good thing.

### Semgrep
- **Pattern matching, not deep analysis.** The open rules largely match shapes in
  the code. It will miss anything requiring you to follow data across function
  or file boundaries.
- **Community rules vary in quality.** Adopt a ruleset without reading it and you
  inherit someone else's opinions as blocking findings.
- **It cannot tell you whether a path is reachable.** A dangerous pattern in dead
  code looks identical to one in a hot path.

### Bandit
- **Python only.** In a polyglot repository it covers a fraction of the code.
- **Semgrep supersedes most of it.** Bandit remains useful for Python-specific
  checks and a long-established rule ID vocabulary, but if you are choosing one,
  Semgrep covers more.
- **Its confidence rating is not severity.** `B101` (assert used) fires on every
  test file and is almost never a real finding — a classic source of alert
  fatigue if you leave it on.

### Checkov
- **Community-edition severity is often null.** Findings arrive with no severity
  at all, so your pipeline has to decide a default. This repo's parser defaults
  to MEDIUM, because a missing severity is not an absent risk.
- **Some checks are opinion, not risk.** "Ensure every security group has a
  description" is good hygiene and not a vulnerability. Blocking merges on it
  trains people to suppress checks.
- **It is slow** on large repositories relative to the alternatives.

### tfsec
- **It is being absorbed into Trivy.** New work goes to Trivy. Running tfsec today
  is reasonable; planning around it long-term is not.
- **Terraform only.**

### Trivy
- **CVE findings have no reachability analysis.** A vulnerability in a package
  you never call is reported the same as one in your request path. On a large
  image this produces hundreds of findings, most of which cannot be exploited in
  your usage — and it is the fastest way to make a security backlog meaningless.
- **Base image churn.** Rebuilding on a new base can change your finding count
  dramatically with no change to your code.
- **Fixes are frequently unavailable.** "No fix available" findings need a
  documented acceptance, not a ticket that sits open forever.

### ASFF / Security Hub
- **It describes what is deployed, not what is in your code.** It cannot tell you
  which module or which commit caused a finding. Mapping back is manual.
- **It costs money at scale**, per finding ingested.
- **It lags.** Config-rule-driven findings can take hours to appear, so it is a
  poor merge gate and a good continuous monitor.
- **Findings can be resolved outside your pipeline**, in the console. Re-ingesting
  them re-opens work someone already closed — which is why this repo's parser
  skips `ARCHIVED` and `RESOLVED` records.

---

## What none of them catch

The most important section, and the reason scanners are a floor rather than a
strategy.

| Not caught | Why |
| --- | --- |
| **Business logic flaws** | "Users can refund an order twice" is not a pattern. No scanner knows your rules |
| **Authorization design errors** | A permission check that is present, correct-looking, and checks the *wrong object* passes every SAST rule ever written |
| **Missing controls** | Scanners find bad configuration. They do not find *absent* configuration — no rule fires because there is no resource to fire on |
| **A control that stopped running** | The one this repository exists for. A scanner that registers zero rules reports a clean scan. See [`silent-failure-patterns.md`](silent-failure-patterns.md) |
| **Intent** | A backdoor written to look like a feature is a code review problem |

This is where threat modelling and human review sit, and why
[`threat-model.md`](threat-model.md) and [`review-standard.md`](review-standard.md)
are in this repository alongside the tooling. **Scanners raise the floor. They do
not raise the ceiling.**

---

## Deciding what to run

### Add a tool when
- It catches a class of problem nothing else does — check the categories first
- You can dedupe its output against what you already have
- Someone owns triaging it

### Remove a tool when
- Its findings are never actioned. **An unactioned scanner is worse than none:**
  it creates triage debt and a false impression of coverage, and both are
  expensive
- Another tool covers it better — running Bandit *and* Semgrep on Python is
  defensible; running three IaC scanners with no deduplication is not
- It has been superseded upstream

### If you are starting from nothing

In this order, and stop wherever your capacity to triage runs out:

1. **Secrets scanning.** Cheapest, fastest, highest-severity findings.
2. **IaC scanning**, if you have infrastructure code. Catches the most damaging
   misconfigurations at the point they are cheapest to fix.
3. **SAST**, one tool, tuned. Not three untuned.
4. **Dependency and container scanning** — but only once you can act on "no fix
   available", or it becomes noise.
5. **CSPM.** The most expensive and the only one that sees reality.

**One tuned scanner beats five untuned ones**, because the failure mode of too
many is that people stop reading any of them — and a backlog nobody reads is
indistinguishable from a clean one.

---

## If you can't afford Wiz or Tenable

Every tool above is open source, and that is deliberate. For *why* an open-source
estate is a legitimate substitute for a commercial platform — capability by
capability — and, just as important, **where it stops** (the attack-path graph
and agentless runtime you do not get), see
[`without-a-commercial-platform.md`](without-a-commercial-platform.md).
