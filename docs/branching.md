# Branching and promotion

Three long-lived branches, one direction of travel, and protection that rises as
a change gets closer to what a reader is shown.

```
feature/*  ─┐
fix/*      ─┼─▶  develop  ──▶  stage  ──▶  main
chore/*    ─┘    integrate     release      published
                                candidate
hotfix/*   ──────────────────────────────▶  main
                                             └─▶ back-merge to stage + develop
```

| Branch | Holds | PR from | Required checks | Reviews | Linear history |
|---|---|---|---|---|---|
| `main` | what a reader is shown | `stage`, `hotfix/*` | all 8 | **1** | no — see below |
| `stage` | release candidate | `develop` | all 8 | 0 | no — see below |
| `develop` | integration | `feature/*`, `fix/*`, `chore/*` | all 8 | 0 | no |

No branch accepts a direct push. Force-push and deletion are disabled on all
three. Conversation resolution is required everywhere.

## Why three, for a repository with one author

Because the argument this repository makes is about *enforced* process, and a
process that exists only in a README is the thing it criticises. The branches
are not ceremony — each one answers a different question:

- **`develop`** — does it work? Every gate runs. Merge order does not matter,
  so linear history is not required here; noise on an integration branch is
  cheap and rebasing feature work repeatedly is not.
- **`stage`** — does it work *together*, in the state it would ship in?
- **`main`** — is it fit to be read by someone deciding whether to hire the
  author? This is the only branch where a review is required.

## The naming convention

```
feature/<short-description>     new capability
fix/<short-description>         defect in existing capability
chore/<short-description>       tooling, docs, dependency bumps
hotfix/<short-description>      urgent, branches from main, merges to main
```

Kebab-case, no ticket numbers — there is no ticket system here, and inventing a
prefix that points at nothing is worse than omitting it.

## Promotion

```bash
# ordinary work
git switch develop && git pull
git switch -c feature/thing
# ... commit ...
gh pr create --base develop

# promote when develop is green
gh pr create --base stage --head develop --title "Promote to stage"
gh pr create --base main  --head stage   --title "Release"
```

A promotion PR carries no new commits. Its purpose is to make the CI suite run
against the exact tree being promoted, and to leave a record of who decided it
was ready.

**Rebase feature branches into `develop`. Merge promotions.**

Learned by using the model rather than by designing it. Requiring linear history
on a promotion branch forces every promotion to be rebase-merged, which replays
`develop`'s commits onto `stage` under new SHAs. The two branches then hold
identical content with different history, and the *next* promotion can neither
fast-forward nor rebase — GitHub refuses it outright:

```
gh pr merge 5 --rebase
  gh pr checkout 5 && git fetch origin stage && git rebase origin/stage
```

The first promotion works, which is why the rule looks correct right up until it
isn't. Linear history belongs to a squash-to-trunk model, where one branch is the
only destination and a merge commit carries no information. In a promotion model
the merge commit *is* the record of the promotion.

## Hotfixes

Branch from `main`, merge to `main`, then **back-merge to `stage` and
`develop` in the same session.** A hotfix that is not back-merged is
reintroduced by the next promotion, which is how a fixed bug returns with
nobody having changed anything — the regression case
[`findings-normalizer`](../findings-normalizer/) exists to detect.

## Protection is applied as code

[`tools/apply_branch_protection.py`](../tools/apply_branch_protection.py) holds
the rules. Configured through a settings page, a protection rule has the same
weakness as a hand-maintained control matrix: correct on the day it is set,
nothing records why, and nobody notices when it changes.

```bash
python tools/apply_branch_protection.py --repo <owner>/Security          # apply
python tools/apply_branch_protection.py --repo <owner>/Security --check  # drift
```

`--check` is the mode worth running on a schedule. The interesting failure is
not *"protection was never configured"* — it is *"protection was configured and
then quietly relaxed."*

**A required status check whose name does not match a real job is not enforced.**
It is simply never satisfied, and GitHub will report the branch as protected
either way. The check names in that file are the `name:` values from
[`ci.yml`](../.github/workflows/ci.yml), and they have to be changed together.
This is the same failure mode as a scanner policy that never registers.

## Two honest limitations

**`enforce_admins` is false.** The repository owner can bypass every rule above.
With one author and no second reviewer, enabling it would deadlock `main`
permanently — the required review could never be satisfied. So these rules
constrain the normal path and do not constrain the owner. In a team that
distinction disappears; here it is real, and stating it is better than implying
an enforcement that is not there.

**A required review cannot be self-approved.** With a single author, the review
requirement on `main` is satisfied by an admin bypass, not by a second pair of
eyes. That is a property of the repository having one contributor, not of the
rule being wrong.
