"""CKV_CAC_1 — Object Lock retention must be COMPLIANCE, not GOVERNANCE.

Checkov's built-in checks verify that Object Lock is *configured*. They do not
verify which mode it is in, and the mode is the entire control.

GOVERNANCE retention can be bypassed by any principal holding
`s3:BypassGovernanceRetention`. An audit trail that a sufficiently privileged
role can delete is a log, not evidence — and a role with that permission is
exactly the role an attacker wants. COMPLIANCE cannot be bypassed by anyone,
including the account root, for the duration of the retention period.

This is the difference between "we enabled Object Lock" on a control matrix and
a control that holds under the threat it exists for.
"""
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck


class ObjectLockComplianceMode(BaseResourceCheck):
    def __init__(self) -> None:
        super().__init__(
            name="S3 Object Lock retention must use COMPLIANCE mode",
            id="CKV_CAC_1",
            categories=[CheckCategories.BACKUP_AND_RECOVERY],
            supported_resources=["aws_s3_bucket_object_lock_configuration"],
        )

    def scan_resource_conf(self, conf) -> CheckResult:
        for rule in conf.get("rule", []) or []:
            if not isinstance(rule, dict):
                continue
            for retention in rule.get("default_retention", []) or []:
                if not isinstance(retention, dict):
                    continue
                mode = retention.get("mode")
                if isinstance(mode, list):
                    mode = mode[0] if mode else None
                if str(mode).upper() == "COMPLIANCE":
                    return CheckResult.PASSED
        return CheckResult.FAILED


check = ObjectLockComplianceMode()
