# Control mapping strategy

## The problem with a spreadsheet

A control matrix maintained by hand is accurate on the day it's written. The infrastructure moves,
the matrix doesn't, and the gap is invisible until an assessor finds it.

## The approach here

Every module declares the controls it implements, in machine-readable form, next to the code that
implements them:

```yaml
# reference-architecture/terraform/modules/audit-logging/controls.yaml
module: audit-logging
implements:
  - id: AU-2
    statement: Event logging is enabled for all management-plane actions
    evidence: trail_enabled + include_management_events assertions in tests
  - id: AU-9
    statement: Audit information is protected from unauthorized modification
    evidence: log_file_validation_enabled + Object Lock on the evidence bucket
  - id: AU-11
    statement: Audit records retained per retention policy
    evidence: retention_days variable asserted >= baseline
```

Three properties follow:

1. **The mapping moves with the code.** Delete the module, the claim goes with it.
2. **Every claim names its evidence.** "We implement AU-9" is an assertion; "log file validation is
   enabled and the test that proves it is here" is a control.
3. **Coverage is computable.** A script folds every `controls.yaml` into a coverage report, so the
   gap analysis is a build artifact rather than an annual exercise.

## The script

[`tools/control_coverage.py`](../tools/control_coverage.py) is what makes property 3 true rather
than aspirational. The generated output is [`control-coverage.md`](control-coverage.md).

```bash
python tools/control_coverage.py --check                        # CI gate
python tools/control_coverage.py --out docs/control-coverage.md # regenerate
```

In `--check` mode it fails the build when:

- a directory contains `.tf` files but no `controls.yaml` — a module whose claims live only in a
  README, which is where control matrices go to become wrong;
- a control entry is missing `statement` or `evidence`;
- a control ID is malformed or names a family that does not exist — a typo'd ID silently produces
  a control nobody implements and nobody misses;
- a declared exception is missing its check, resource or reason.

CI also diffs the committed report against a freshly generated one, so the artifact cannot drift
from the code that produced it. The parser is deliberately strict and dependency-free: a lenient
parser that skipped what it did not understand would under-report coverage, and under-reported
coverage reads as success.

## Exceptions are part of the mapping

Each `controls.yaml` also declares its policy exceptions:

```yaml
exceptions:
  - check: CKV_AWS_144
    resource: aws_s3_bucket.audit
    reason: Cross-region replication is a caller-level availability decision, not a
      tamper-evidence control
```

They appear in the coverage report next to the controls. An exception you can read and argue with
is a control decision; an exception hidden behind `soft_fail` is a gap. The repository has ten, all
inline at the resource, all with reasons.

## What this deliberately does not do

It does not claim a control is *satisfied*. It claims the technical control is *implemented and
enforced*. Satisfaction is an assessor's judgment and depends on policy, procedure and scope that
live outside the repository. Conflating the two is how organizations get surprised at assessment.
