# Reference architecture

A FedRAMP Moderate–aligned AWS security foundation, expressed as Terraform modules.

**Written from public standards.** NIST SP 800-53 Rev 5, the FedRAMP Moderate baseline, CIS
Benchmarks and the AWS Foundational Security Best Practices standard. Nothing here is derived from
any employer environment.

## Modules

| Module | Purpose | Controls |
|---|---|---|
| `audit-logging` | Management-plane audit trail, log-file validation, immutable retention | AU-2, AU-9, AU-11 |
| `detective-controls` | Threat detection, config rules, posture aggregation | SI-4, CM-6, RA-5 |
| `kms-encryption` | Customer-managed keys, rotation, envelope encryption | SC-12, SC-13, SC-28 |
| `iam-baseline` | Least-privilege roles, permission boundaries, no static credentials | AC-2, AC-6, IA-2 |
| `network-isolation` | Private subnets, endpoints, segmentation, WAF | SC-7, AC-4 |
| `eks-baseline` | Private endpoint, workload identity, pod security, network policy | AC-3, SC-7, AU-2 |
| `evidence-bucket` | Immutable evidence store with object lock | AU-9, AU-11 |

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
