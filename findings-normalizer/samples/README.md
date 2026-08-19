# Sample scanner outputs (fixtures)

One representative output file per supported parser — used as test fixtures and as
the `--input` for the [README's](../README.md#usage) quickstart.

**These are synthetic.** File paths, commit hashes and authors are invented, and
every secret value is the literal `REDACTED-BY-FIXTURE-NEVER-A-REAL-VALUE` — a real
scanner's output is never committed here. The *shapes*, though, are faithful to
what each tool actually emits, and they carry the edge cases the parsers are
tested against: Checkov's list-vs-dict output, ASFF's `GeneratorId`, and the
tfsec/Trivy shared rule ID that must fold into one finding. See
[the parser notes](../README.md#parser-notes-worth-reading).

| File | Parser | Tool class |
|---|---|---|
| `asff.json` | AWS Security Hub (ASFF format) | cloud posture |
| `bandit.json` | Bandit | SAST (Python) |
| `checkov.json` | Checkov | IaC |
| `gitleaks.json` | Gitleaks | secrets |
| `semgrep.json` | Semgrep | SAST |
| `tfsec.json` | tfsec | IaC |
| `trivy.json` | Trivy | container + IaC |

A parametrized test (`tests/test_parsers.py`) walks the parser registry and fails
if any supported tool is missing its fixture here — a parser with no sample is a
parser nobody has run.
