# tools

The machinery behind the repository's central claim: that its evidence is
**generated and gated, not asserted**. Every "computable" or "diffed in CI" line
elsewhere in the repo is made true by a script here. Each one has a full
docstring at the top of the file — this is the index.

## Generators — output is committed, and CI fails if it drifts

Each writes an artifact with no flag, and re-checks the committed copy with
`--check`. A stale diagram, metric, or coverage report fails the build, so the
artifact can never quietly diverge from the code.

| Script | Generates | Run it | Drift check |
|---|---|---|---|
| [`render_diagrams.py`](render_diagrams.py) | every SVG in `docs/diagrams/` (drawn from data, not exported from a tool) | `python tools/render_diagrams.py` | `--check` |
| [`repo_metrics.py`](repo_metrics.py) | `docs/metrics.md` — every number with its unit named | `python tools/repo_metrics.py` | `--check` |
| [`control_coverage.py`](control_coverage.py) | `docs/control-coverage.md` from each component's `controls.yaml` | `python tools/control_coverage.py --out docs/control-coverage.md --component .github/controls.yaml` | `--check` |

> If you edit code that changes a count, a diagram, or a control mapping,
> regenerate **after** the edit and commit the result — CI runs the `--check`
> form and a stale artifact turns the build red.

## Gates — CI fails the build on a policy violation

| Script | Fails when | Run it |
|---|---|---|
| [`check_repo_hygiene.py`](check_repo_hygiene.py) | personal, career, or credential material is tracked (a job-search log once reached the repo via the web UI, which never consults `.gitignore`) | `python tools/check_repo_hygiene.py` |

## Admin — run on demand, not in CI

| Script | Does | Run it |
|---|---|---|
| [`apply_branch_protection.py`](apply_branch_protection.py) | branch protection **as code** — reviewable in a diff, idempotent to re-apply | `python tools/apply_branch_protection.py --repo owner/name` · `--check` reports drift without changing anything (worth scheduling) |

Requires the `gh` CLI with admin on the repo. Kept out of CI because it *changes*
repository settings; the interesting failure it guards against is "protection was
configured and then quietly relaxed."

## Tests — the tools have to fail when they should

`test_*.py` here assert the negative case, because a checker that only ever passes
is indistinguishable from no checker:

- [`test_render_diagrams.py`](test_render_diagrams.py) — every diagram is legible, fluid, and self-contained (no CDN, no `<script>`).
- [`test_control_coverage.py`](test_control_coverage.py) — the coverage checker fails on a module with no `controls.yaml`, a malformed control ID, or evidence missing.
- [`test_check_repo_hygiene.py`](test_check_repo_hygiene.py) — the hygiene gate actually flags a planted resume/credential, not just clean trees.

(`repo_metrics.py` has no separate test — its drift check *is* its test: CI regenerates it and diffs.)

```bash
python -m pytest tools -q
ruff check tools
```
