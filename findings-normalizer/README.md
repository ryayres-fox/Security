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
- **Append-only history.** Every scan writes a new observation; the current state is a fold over
  history. You can answer "when did this first appear?" and "did it come back?"
- **Cross-tool dedupe.** Findings that resolve to the same location and control are merged, with
  every reporting tool retained as an attribution.
- **Disposition, not just severity.** `ACTIVE`, `RESOLVED`, `ACCEPTED` (requires an owner, a
  compensating control and an expiry), `FALSE_POSITIVE` (requires a reason).

> **A note on false positives, learned the hard way:** if the store has no field for it, you cannot
> report a false-positive rate later, no matter how good your query is. That's a schema decision,
> not a reporting decision. This schema has the field.

## Usage

```bash
pip install -e .
findings-normalize ingest --tool trivy   --input samples/trivy.json
findings-normalize ingest --tool semgrep --input samples/semgrep.json
findings-normalize report --format html --out report.html
findings-normalize gate   --fail-on critical,high   # exit 1 for CI
```

## Supported parsers

`trivy` · `checkov` · `tfsec` · `semgrep` · `bandit` · `gitleaks` · `asff` (AWS Security Hub)

Adding one is a single file implementing `parse(raw: dict) -> list[Finding]`.
