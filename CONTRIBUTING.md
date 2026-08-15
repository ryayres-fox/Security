# Contributing

Read [`docs/review-standard.md`](docs/review-standard.md) once. It carries the
posture — default-BLOCK, evidence on the change rather than the reviewer,
unverified defaults to High — and everything below assumes it.

## The path in

`feature/*` → **main**. One long-lived branch, short-lived feature branches,
squash or rebase on merge.

There is no direct push to `main` and no exception for the owner —
`enforce_admins` is on. Required approving reviews are **zero**, which is
stronger than it sounds: a solo author cannot self-approve, so a review
requirement could only ever be met by an admin bypass, and a rule you step over
every time trains stepping over rules. Full reasoning in
[`docs/branching.md`](docs/branching.md).

## Before you open a pull request

```bash
pytest findings-normalizer/tests ai-security tools -q   # no -k, no --ignore
pytest policies -q                                      # needs checkov
ruff check findings-normalizer ai-security tools policies
terraform fmt -check -recursive reference-architecture/
checkov -d reference-architecture/ --compact            # 0 failed
python tools/control_coverage.py --check
python tools/repo_metrics.py --check
python tools/render_diagrams.py --check
python tools/check_repo_hygiene.py
```

The last three are drift checks. Generated artifacts are committed, so if you
changed code that feeds them, regenerate and commit the result — CI diffs it.

Install the hook once: `git config core.hooksPath .githooks`.

## Rules that are not style preferences

**Every new behaviour needs a test that fails when the behaviour is removed.**
A test that passes against both the fixed and the broken implementation proves
nothing. Where practical, demonstrate it — this repository keeps deliberately
broken implementations (`LeakyStore`, `StarvedStore`) so the tests that
distinguish them are provably load-bearing.

**Scanner exceptions are inline, at the resource, with a written reason, and
declared in `controls.yaml`.** `soft_fail` is never acceptable: it makes
everything pass and therefore means nothing.

**Every `uses:` is pinned to a 40-character SHA you resolved against the API** —
not a tag, and not a plausible-looking SHA. This repository shipped one that did
not exist, and the gate never ran once.

**Constraints belong in `validation` blocks, not comments.** A comment saying
"don't use a wildcard here" is advice, and advice does not survive a deadline.

**Nothing employer-specific, ever.** No employer or client name, no account ID,
ARN, hostname, or environment identifier — including in fixtures. Everything is
written from public standards against synthetic targets. `repo hygiene` enforces
it on tracked files, but it is a backstop, not a substitute for judgement.

## The one question worth asking

> **Could this check have failed?**

Not *what did it report*. See
[`docs/silent-failure-patterns.md`](docs/silent-failure-patterns.md) for four
worked examples, three of them defects in this repository's own code.
