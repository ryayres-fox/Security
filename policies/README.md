# Custom policies

Three Checkov policies, and — more importantly — the tests that prove they run.

```bash
pip install checkov pytest
pytest policies -q          # 11 tests
```

## The policies

| ID | Rule | Why no built-in check covers it |
|---|---|---|
| `CKV_CAC_1` | S3 Object Lock retention must be `COMPLIANCE` | Built-ins verify Object Lock is *configured*. The **mode** is the control: `GOVERNANCE` can be bypassed by any principal holding `s3:BypassGovernanceRetention`, which is exactly the principal an attacker wants |
| `CKV_CAC_2` | IAM roles must carry a permissions boundary | Whether boundaries are mandatory is an organizational decision, so no scanner ships it. Here it is required, and therefore expressed as code rather than as a sentence in a README |
| `CKV_CAC_3` | OIDC trust policies must match `sub` exactly | `StringLike` with `repo:org/repo:*` trusts every branch, tag and — often — every fork PR. The policy reads correctly in review, and anyone who can push a branch can assume the role |

## Why this directory exists

A previous set of custom policies **had never executed.** There was no
`__init__.py` in the policy directory, so Checkov's external-checks loader
registered zero checks. The scan completed normally, reported its usual counts,
and CI went green. Nothing anywhere indicated the policies were not running.

The failure reproduces on current Checkov. From this repository's own fixtures:

```
WITHOUT __init__.py :  11 checks reported, CKV_CAC_1 present: False
WITH    __init__.py :  12 checks reported, CKV_CAC_1 present: True
```

Both runs exit the same way. The only difference is a number nobody was
counting.

## The two assertions

`test_policy_registration.py` asserts two separate things, because **either one
alone is a fail-open**:

1. **The loader registered the checks.** Catches the packaging failure — policies
   present in the repository, absent from the scan.
2. **A known-bad fixture actually produces a finding.** Catches the subtler case
   where checks register perfectly and never match, because a resource type is
   misspelled or `conf` changed shape in a Checkov upgrade. *A check that
   registers and never fires is the same fail-open, relocated one step later.*

Plus the compliant fixture, which matters as much as the non-compliant one: a
policy set that fails everything passes every "does it fire?" test and is still
useless, because it gets suppressed within a week — and a suppressed check
reports success forever after.

And one meta-assertion: that removing `__init__.py` really does break
registration *silently*, verifying that assertion 1 is load-bearing rather than
passing for an unrelated reason. Try it:

```bash
mv policies/checkov/__init__.py /tmp/ && pytest policies -q
# 10 failed, 1 passed
mv /tmp/__init__.py policies/checkov/ && pytest policies -q
# 11 passed
```

The expected check IDs are parsed out of the policy source at collection time
rather than hardcoded, so adding a policy that fails to register fails this
suite. A hardcoded list would keep passing.

## Adding a policy

1. Write `check_<name>.py` in `checkov/`, ending with `check = YourCheck()`.
2. Add a violating resource to `fixtures/noncompliant/main.tf` and a compliant
   twin to `fixtures/compliant/main.tf`.
3. Run `pytest policies -q`. The parametrized tests pick the new ID up
   automatically — there is no list to update, which is the point.

If a new check registers but will not fire, the fixture is wrong or the
`supported_resources` string is. Both are worth finding now rather than during
an assessment.

## The generalisable point

> **A control reporting success is not evidence that it ran.**

The question that finds this class of defect is *"could this check have
failed?"* — not *"what did this check report?"* Reading the output would never
have surfaced it, because the output was indistinguishable from a clean scan.
