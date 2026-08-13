# Controls that fail silently

Four patterns, each one a control that reported success while enforcing nothing.
Three were found in this repository. One is a design lesson from elsewhere,
described at the level of mechanism.

They share a single property, and it is the reason they are collected here:

> **A control reporting success is not evidence that it ran.**

The question that finds all four is *"could this check have failed?"* — not
*"what did this check report?"* Reading output would never have surfaced any of
them, because in every case the output was indistinguishable from a clean run.

---

## 1. The policy set that registered zero checks

A set of custom scanner policies existed in the repository, was referenced by
the CI configuration, and had never executed. The policy directory had no
`__init__.py`, so the external-checks loader registered nothing. The scan
completed normally, reported its usual counts, and CI went green.

Reproduced on current tooling in [`policies/`](../policies/):

```
WITHOUT __init__.py :  11 checks reported, custom check present: False
WITH    __init__.py :  12 checks reported, custom check present: True
```

Both runs exit identically. The difference is a number nobody was counting.

**Why it is invisible:** there is no error, no warning, and no missing output —
only *less* output, in a place where nobody had established what the right
amount was.

**The fix that generalises** is not the `__init__.py`. It is asserting two
things in CI: that the loader registered the expected checks, **and** that a
known-bad fixture actually produces a finding. Either alone is a fail-open — a
check that registers and never fires is the same defect relocated one step
later.

---

## 2. The scan gate pinned to a commit that does not exist

This repository's CI declared an infrastructure-scanning gate with
`soft_fail: false` and pinned the scanning action to a 40-character SHA. Pinned
by digest rather than tag, failing closed, comment naming the version — correct
by every signal available from reading it.

The SHA did not exist:

```
GET /repos/<action>/commits/99bb2caf247dfd9dfd22e0a6f6dcc16ea99e0c60
422  "No commit found for SHA"
```

The reference is resolved before the job starts, so the job failed at startup on
every run since the repository was created. The gate had never executed once.

**Why it is invisible:** a control that reports nothing looks exactly like a
control that finds nothing. Silence is the same in both cases.

**What generalises:** correct *form* is not correct *function*. Every format
check passed — 40 hex characters, plausible value, version comment. Only
resolving the reference against the API found it. Verifying an enforcement path
is a different activity from reading a diff, and only the first one catches this.

---

## 3. The ignore file that was never consulted

A file that must never be published reached this repository's default branch
through a web-UI upload. The obvious remedy — add it to `.gitignore` — would not
have prevented it and would not prevent a recurrence.

`.gitignore` is client-side. A web upload never reads it. It has no effect on a
file that is already tracked. `git add -f` overrides it silently.

**Why it is invisible:** the ignore file *looks* like a control. It is checked
into the repository, it is reviewed, it lists the right patterns. Nothing about
reading it reveals that the path which actually delivered the file never
consulted it.

**What generalises:** a control has to sit on the path the risk travels. Ask
which paths reach the asset, then ask which of them the control is on.
[`tools/check_repo_hygiene.py`](../tools/check_repo_hygiene.py) reads
`git ls-files` — what is actually tracked — and runs on a machine that is not the
author's.

---

## 4. The guard whose correctness depended on the workload

A scale-down guard tested a repository-wide "work in progress" count before
releasing capacity for any individual pool. That was correct while the
repository had quiet gaps. When delivery moved to many small pull requests, the
repository was never quiet, and the guard silently became *"never scale down."*

Nothing in the file changed. The workload shape changed underneath it. The
checker ran every five minutes and reported zero errors the entire time — the
only symptom was cost. The fix was to scope the guard to the pool's own busy
count.

**Why it is invisible:** the component was healthy by every measure it exposed.
It ran on schedule, it completed, it logged no errors. Its *decision* was wrong,
and a decision is not an error.

**What generalises**, and it is the most portable lesson here:

> **A guard whose correctness depends on a property of the workload, rather than
> on a property of the thing it guards, will fail silently when the workload
> changes — and it will fail with zero errors.**

The guard asked a question about the whole repository in order to make a
decision about one pool. That mismatch of scope was the defect, and it was
latent from the day it was written. It became visible only when the workload
crossed a threshold nobody had identified as a threshold.

---

## What to do with this

The four have a common remedy shape, and it is not "add more scanners":

1. **Assert the control's own liveness, not just its verdict.** Count the checks
   that registered. Resolve the reference. Confirm the path is the one the risk
   travels.
2. **Keep a known-bad fixture and require it to fail.** This is the cheapest
   possible proof that a control still matches something. It is also the only
   one that survives an upgrade changing an internal data shape.
3. **Ask what this guard assumes about its environment**, and whether anything
   would tell you if the assumption stopped holding.
4. **Watch every gate fail at least once, on purpose.** A gate nobody has seen
   fail is a gate nobody knows works. This repository's CI asserts that its
   findings gate exits *non-zero* against fixtures containing critical findings,
   for exactly this reason.
