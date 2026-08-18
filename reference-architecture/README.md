# Reference architecture

A FedRAMP Moderate–aligned AWS security foundation, expressed as Terraform modules.

**Written from public standards.** NIST SP 800-53 Rev 5, the FedRAMP Moderate baseline, CIS
Benchmarks and the AWS Foundational Security Best Practices standard. Nothing here is derived from
any employer environment.

## Modules

| Module | Purpose | Controls |
| --- | --- | --- |
| `audit-logging` | Management-plane audit trail, log-file validation, immutable retention, real-time delivery | AU-2, AU-6, AU-9, AU-11, AC-6, SC-8, SI-4 |
| `iam-baseline` | Permission boundaries, OIDC workload identity, no static credentials | AC-2, AC-4, AC-6, AC-6(5), IA-2, IA-2(1), IA-5, IA-5(1), AU-9 |

Two modules, both complete. There is no table row here for a module that does
not exist — a list of seven names where five are empty directories is the same
category of claim as a control that is documented but not enforced, and this
repository is not the place to make it.

The obvious next one is `network-isolation`. It is also the one worth doing
properly rather than quickly: an encryption module tends to converge on the
provider documentation, while segmentation decisions are where the judgement
actually shows.

Each module ships a `controls.yaml`, a README, and plan-time validation that proves the control
rather than asserting it. See [`../docs/control-mapping.md`](../docs/control-mapping.md) for the
strategy and [`../docs/control-coverage.md`](../docs/control-coverage.md) for the generated report.

## Status

**Implemented:** `audit-logging`, `iam-baseline`. Both are `terraform validate` clean, `fmt` clean,
and pass Checkov with zero failures and only inline, justified skips.

**Scaffolded:** the remaining five. Build them in the order your own story needs, not the order
they're listed.

## Standards every module here meets

- `terraform validate` and `terraform fmt -check` clean, enforced in CI across every module directory
- Checkov with `soft_fail: false`. Exceptions are inline at the resource with a written reason, and
  declared in `controls.yaml` so they appear in the coverage report
- A `controls.yaml` in which every control names its **evidence**, not just its ID —
  `tools/control_coverage.py --check` fails the build otherwise
- Constraints expressed as `validation` blocks so the wrong value fails at plan time rather than at
  assessment

## Verifying the whole tree

```bash
terraform fmt -check -recursive reference-architecture/
checkov -d reference-architecture/ --compact     # 114 passed, 0 failed, 10 skipped
python tools/control_coverage.py --check
```
