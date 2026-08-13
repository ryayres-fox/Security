# audit-logging

Management-plane audit trail with tamper-evident storage.

## What it enforces

| Control | How |
|---|---|
| **AU-2** | Multi-region trail with global service events — no region is a blind spot |
| **AU-9** | Log-file validation on, Object Lock in COMPLIANCE mode, versioning, public access blocked, KMS encryption with a customer-managed key |
| **AU-11** | Retention validated at plan time; the module refuses to build below the baseline |

## Two decisions worth explaining

**Object Lock in `COMPLIANCE` mode, not `GOVERNANCE`.** GOVERNANCE can be bypassed by a principal
holding `s3:BypassGovernanceRetention`. If your audit trail can be deleted by a sufficiently
privileged role, it is not evidence — it's a log.

**Retention is validated, not documented.** A `validation` block means the wrong value fails at
plan time. A comment saying "should be 365" means the wrong value ships and gets found at
assessment.

## Usage

```hcl
module "audit_logging" {
  source         = "./modules/audit-logging"
  bucket_name    = "example-audit-logs-${random_id.suffix.hex}"
  trail_name     = "example-management-trail"
  kms_key_arn    = module.kms.audit_key_arn
  retention_days = 365
}
```
