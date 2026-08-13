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

## What this deliberately does not do

It does not claim a control is *satisfied*. It claims the technical control is *implemented and
enforced*. Satisfaction is an assessor's judgment and depends on policy, procedure and scope that
live outside the repository. Conflating the two is how organizations get surprised at assessment.
