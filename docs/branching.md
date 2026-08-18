# Branching

One long-lived branch, short-lived feature branches, and rules that apply to
everyone — including the owner.

```
feature/*  ─┐
fix/*      ─┼──▶  main
chore/*    ─┘
```

| | |
| --- | --- |
| **Required checks** | all 10, strict — the branch must be up to date |
| **Pull request** | required. No direct push, for anyone |
| **Approving reviews** | **0** — see below |
| **`enforce_admins`** | **true** — the owner is not exempt |
| **Force push / deletion** | disabled |
| **Linear history** | required — squash or rebase your feature branch |
| **Conversation resolution** | required |

Applied as code by
[`tools/apply_branch_protection.py`](../tools/apply_branch_protection.py), with a
`--check` mode that reports drift. The interesting failure is not *"protection
was never configured"* — it is *"protection was configured and then quietly
relaxed."*

---

## Why zero required reviews is stronger here, not weaker

This looks like a relaxation and is the opposite.

The previous model required one approving review on `main`. With a single
author, that requirement **can only ever be satisfied by an admin bypass** —
GitHub does not allow self-approval. So every merge used `--admin`, every merge
stepped over the rule, and the bypasses are visible in the git history.

A rule you step over every time is not a rule. It is worse than no rule, because
it trains the habit of stepping over rules and it produces an audit trail that
says so.

So the requirement that could not be met was removed, and in exchange
**`enforce_admins` was turned on**. The owner now has no path around:

- no direct push to `main`
- no merging with a red check
- no force-push, no branch deletion
- no `--admin` escape hatch

Net: every change goes through a pull request and ten green checks, with no
exceptions for anyone, and nothing deadlocks waiting for a second person who
does not exist.

**The honest limitation:** an owner can still edit the protection rules
themselves. No branch protection defends against the account that administers
it. What it does defend against is the ordinary failure — a hurried direct push
at the end of a long day — which is the one that actually happens.

---

## Why the three-branch model was removed

`develop → stage → main` is correct for a team with reviewers and a release
cadence. With one author it cost:

- **three or four pull requests per change**, each waiting on a full CI run
- a review requirement satisfiable only by bypass
- **four reconciliation branches** to unpick a divergence the model itself
  created — requiring linear history on a promotion branch forces rebase-merges,
  which replay commits under new SHAs, after which the *next* promotion can
  neither fast-forward nor rebase

The last one is worth keeping in mind if you ever add the branches back: the
first promotion works, which is why the rule looks correct right up until it
isn't. Rebase feature branches; merge promotions.

Ceremony is what gets a process abandoned. A model that is followed beats a
better model that is not.

---

## Working in it

```bash
git switch main && git pull
git switch -c feature/thing
# ... commit ...
gh pr create --base main
```

Before opening the pull request, run what CI will run — the list is in
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Generated artifacts are committed and
diffed, so regenerate them if you changed the code that feeds them.

Install the hook once:

```bash
git config core.hooksPath .githooks
```

It is convenience, not the control. Hooks are not distributed with a clone and
`--no-verify` skips them. CI is the control.

## Merging

Squash or rebase. Merge commits are disabled at the repository level, so
`main` stays linear and readable — which matters more here than usual, because
the commit history is part of what the repository is showing.

Delete the branch on merge. GitHub does it automatically.
