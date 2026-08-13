<!--
This template is short on purpose. The long-form reasoning, the severity scale
and the verdict format live in docs/review-standard.md — read that once, then
this becomes a two-minute fill-in.

The one section that is not optional is the Verification Ledger. A PR without
one is reviewable only on process grounds, because nothing in it has been shown
to work.
-->

## What this changes

<!-- One paragraph. What moved, and why now. Link the issue if there is one. -->

## What proves it — Verification Ledger

**What you *ran*, and what it *returned*.** Not what you read, not what you
intend to run. Paste real output or a run link.

| # | Command | Result | What it proves |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

Anything you could **not** run goes here, with the reason. A stated blind spot
costs nothing; an unstated one gets found by the next person to trust this.

- Not run:

## Control impact

<!-- Delete this section only if the diff touches no Terraform, no CI gate, no
     authorization path, and no parser. If you are unsure, it applies. -->

- **Controls added or changed:** <!-- e.g. AC-6, AU-9 — must match controls.yaml -->
- **`controls.yaml` updated, with an `evidence` field for each claim:** yes / no / n/a
- **`python tools/control_coverage.py --check` passes:** yes / no
- **Coverage report regenerated** (`--out docs/control-coverage.md`): yes / no / unchanged

## Policy exceptions

<!-- Every scanner suppression. If none, write "None". Never `soft_fail`. -->

| Check | Resource | Why this does not apply |
|---|---|---|
| | | |

## Checklist

Tick what you verified. An unticked box is information, not a failure — leaving
it blank and saying why is better than ticking it because it was probably fine.

- [ ] `pytest findings-normalizer/tests ai-security tools -q` passes, **with no
      `-k`, `--ignore`, `--deselect` or `--skip`**, and the collected count did
      not drop
- [ ] `ruff check findings-normalizer ai-security tools` clean
- [ ] `terraform fmt -check -recursive reference-architecture/` and `validate` clean
- [ ] `checkov -d reference-architecture/` — 0 failed; every skip is inline, at
      the resource, with a reason
- [ ] Every `uses:` in a changed workflow is pinned to a **40-character SHA that
      I resolved against the API**, not to a tag and not to a SHA I copied from
      somewhere plausible
- [ ] New behaviour has a test that **fails when the behaviour is removed**
- [ ] No secret, credential, account ID, ARN, internal hostname or real domain
      appears anywhere in the diff — including in fixtures
- [ ] No machine-local path (`/Users/…`, `C:\Users\…`), scratchpad path, or
      chat/artifact URL in the diff, the commits, or this PR body
- [ ] Docs changed alongside the code they describe

## Scope

- [ ] Every file in this diff belongs to the stated change. Anything incidental
      is called out below.

<!-- Unrelated changes, and why they are here: -->
