# audit-logging

Management-plane audit trail with tamper-evident storage, a real-time notification path, and no
unjustified policy exceptions.

## What it enforces

| Control | How |
|---|---|
| **AU-2** | Multi-region trail with global service events — no region is a blind spot |
| **AU-6** | Trail delivered to CloudWatch Logs so metric filters and alarms can act on it in near real time |
| **AU-9** | Log-file validation on, Object Lock in COMPLIANCE mode, versioning, public access blocked, KMS encryption with a customer-managed key, TLS-only bucket policy |
| **AU-11** | Retention validated at plan time; the module refuses to build below the baseline |
| **AC-6** | Delivery role scoped to this trail's own log streams, with an optional permissions boundary |
| **SC-8** | Explicit deny on `aws:SecureTransport=false` for both buckets |
| **SI-4** | Object-created events published to an encrypted SNS topic |

## Decisions worth explaining

**Object Lock in `COMPLIANCE` mode, not `GOVERNANCE`.** GOVERNANCE can be bypassed by a principal
holding `s3:BypassGovernanceRetention`. If your audit trail can be deleted by a sufficiently
privileged role, it is not evidence — it's a log.

**Retention is validated, not documented.** A `validation` block means the wrong value fails at
plan time. A comment saying "should be 365" means the wrong value ships and gets found at
assessment.

**The audit bucket has no lifecycle `expiration` rule, only transitions.** Under a COMPLIANCE lock
an expiration action cannot delete anything until the retention period lapses. Writing one anyway
would produce a lifecycle policy that reads like a deletion schedule and does not delete — the kind
of control that looks right in a review and does nothing. The retention period *is* the deletion
schedule.

**`aws:SourceArn` on every service principal grant.** A bucket policy that trusts
`cloudtrail.amazonaws.com` without an ARN condition can be used by *any* account's trail. That is
the confused-deputy path, and it is the default shape of most published CloudTrail bucket policies.

**The delivery role cannot write to arbitrary log groups.** The common form of this policy is
`logs:*` on `*`, which grants the trail's role write access to every log group in the account —
including the ones that would record its misuse. Here it is scoped to the trail's own log-stream
prefix.

## Policy exceptions

Five Checkov checks are skipped. Each is skipped inline, at the resource, with a written reason —
never with `soft_fail`. Run `checkov -d reference-architecture/` and read them:

| Check | Resource | Why |
|---|---|---|
| `CKV_AWS_18` | `access_logs` | This bucket *is* the access-log target; logging it to itself is a write loop, and a third bucket relocates the question without answering it |
| `CKV_AWS_145` | `access_logs` | S3 server access logging cannot deliver to a CMK-encrypted bucket — a platform constraint. SSE-S3 applied; the alternative was no access logging at all |
| `CKV_AWS_144` | `audit`, `access_logs` | Cross-region replication is a caller-level availability decision with real cost. The tamper-evidence property this module owns comes from Object Lock and digest files, which replication does not improve |
| `CKV2_AWS_62` | `access_logs` | Event notifications would fire in proportion to read volume, at cost, with no detection value |

The point of the table is that an exception you can read and argue with is a control decision. An
exception you can't see is a gap.

## Usage

```hcl
module "audit_logging" {
  source      = "./modules/audit-logging"
  bucket_name = "example-audit-logs-${random_id.suffix.hex}"
  trail_name  = "example-management-trail"
  kms_key_arn = module.kms.audit_key_arn

  retention_days            = 365   # Object Lock COMPLIANCE, AU-11 floor
  cloudwatch_retention_days = 365
  access_log_retention_days = 90
  permissions_boundary_arn  = module.iam_baseline.boundary_arn
}
```

## Verifying it

```bash
terraform init -backend=false && terraform validate
checkov -d . --compact          # 0 failed, 5 skipped-with-reason
```

The KMS key must allow `cloudtrail.amazonaws.com` and `logs.<region>.amazonaws.com` to generate
data keys, or the trail and the log group will both fail to start. That grant belongs to the
`kms-encryption` module, not this one.
