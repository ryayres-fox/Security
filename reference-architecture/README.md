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

Each module ships a `controls.yaml`, a README, and tests that prove the control rather than assert
it. See [`../docs/control-mapping.md`](../docs/control-mapping.md).

## Status

`audit-logging` is implemented as the worked example. The rest are scaffolded — build them in the
order your own story needs, not the order they're listed.
