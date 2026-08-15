# findings-normalizer

Scanner sprawl is the normal condition of a mature pipeline: IaC scanners, container scanners,
SAST, secrets detection, dependency analysis, cloud posture. Each writes a different shape, each
re-reports the same issue on every run, and none of them knows about the others.

This normalizes them into one record with a **stable identity**, so a finding can be assigned,
owned, risk-accepted with a compensating control, and closed with evidence — and so the same issue
found by three tools is one finding, not three.

## Design

- **Stable identity.** `sha256(tool_class, rule_id, file_path, resource_id)` — survives re-scans,
  line-number drift, and tool version bumps.
- **Shared rule IDs, not vendor names.** tfsec and Trivy draw on the same rule database and both
  report `AVD-AWS-0107`, but tfsec *also* calls it `aws-vpc-no-public-ingress-sgr`. Hashing the
  friendlier name splits one misconfiguration across two tools that never disagreed. The vendor's
  name is kept as `native_rule_id`, for display only.
- **Append-only history.** Every scan writes an immutable `Observation`; current state is a fold
  over that log. This is what makes "when did this first appear?" and "did it come back?"
  answerable at all.
- **Cross-tool dedupe.** Findings resolving to the same rule and location merge, with every
  reporting tool retained as an attribution. Agreement across tools is signal.
- **Disposition, not just severity.** `ACTIVE`, `RESOLVED`, `ACCEPTED` (requires an owner, a
  compensating control and an expiry), `FALSE_POSITIVE` (requires a reason).
- **Acceptances expire.** A lapsed acceptance counts as active again and re-blocks the gate. An
  expiry nobody enforces is a permanent waiver wearing a deadline.

> **A note on false positives, learned the hard way:** if the store has no field for it, you cannot
> report a false-positive rate later, no matter how good your query is. That's a schema decision,
> not a reporting decision. This schema has the field.

> **A note on secrets:** the Gitleaks parser never reads `Secret` or `Match` into a record, and
> there is a test that asserts it. A normalizer that copies the matched credential into its own
> JSON has taken a leak that existed in one place and written it to a second one — usually an
> artifact, frequently uploaded by CI. The tool that finds the leak must not be the tool that
> spreads it.

## Usage

```bash
pip install -e .

findings-normalize ingest --tool trivy   --input samples/trivy.json
findings-normalize ingest --tool semgrep --input samples/semgrep.json
findings-normalize report --format html --out report.html
findings-normalize gate   --fail-on critical,high   # exit 1 for CI
```

State persists to `.findings-store.json` between invocations, because `ingest` and `gate` are
separate CI steps in separate processes. Use `--state` to relocate it, and `--scan-date` to backfill
history.

Running all seven samples gives 19 tracked findings from 20 parsed — the tfsec/Trivy overlap folds
into one record attributed to both tools:

```
tfsec: parsed 2 · 1 new · 1 merged into existing · 12 tracked total
```

The HTML report is a single self-contained file: no scripts, no external assets, light and dark.
A report that needs a CDN renders blank inside the networks where this tooling actually runs — and
there is a test asserting no `http://`, `https://` or `<script>` appears in the output.

## Supported parsers

`asff` (AWS Security Hub) · `bandit` · `checkov` · `gitleaks` · `semgrep` · `tfsec` · `trivy`

**What each of these is for, when it runs, and when *not* to use it:**
[`docs/scanner-strategy.md`](../docs/scanner-strategy.md). Worth reading before adopting this —
overlap without deduplication is worse than a single tool, and that document explains which
overlaps are deliberate.

Note that **ASFF is not a scanner**. It is the AWS Security Finding Format, the JSON shape AWS
Security Hub emits when GuardDuty, Inspector and Config report. The parser exists so cloud findings
land in the same store as everything else.

Adding one is a single file implementing `parse(raw) -> list[Finding]`, plus one line in the
registry. Every supported tool must ship a fixture in `samples/` — a parametrized test walks the
registry and fails if one is missing, because a parser with no fixture is a parser nobody has run.

## Parser notes worth reading

| Tool | The thing that bites you |
|---|---|
| `checkov` | Emits a **list** when several frameworks run in one invocation, a dict otherwise. Handling only the dict form returns zero findings and a green build — a silent fail-open |
| `checkov` | Community edition leaves `severity` null. A missing severity is not an absent risk, so it defaults to MEDIUM rather than INFO |
| `trivy` | The resource is in `CauseMetadata.Resource`. `Resolution` is remediation prose — keying on it produces a finding identified by a sentence that changes when the tool rewords it |
| `asff` | Use `GeneratorId`, not `Id`. `Id` is per-resource and unique per finding, which defeats dedupe entirely |
| `asff` | Skip `ARCHIVED` / `RESOLVED` records. Re-opening closed work is the fastest way to make a normalizer distrusted |
| `bandit` | Reports severity *and* confidence. Confidence is a triage input, not a property of the risk; folding it into severity conflates two questions |

## Tests

```bash
pip install -e ".[dev]"
pytest -q     # 50 tests
ruff check src
```

The suite covers identity stability, cross-vendor merge on real output shapes, regression detection
across scan dates, acceptance expiry, disk round-trip, and the README's own quickstart commands —
so documentation drift fails the build rather than being discovered by whoever clones the repo.
