"""CKV_CAC_2 — IAM roles must carry a permissions boundary.

A least-privilege policy that the role itself can rewrite is least-privilege
only until someone tries. The boundary is the ceiling that survives a later
policy attachment, whoever makes it and whether or not they meant to.

Checkov has no built-in check for this, because whether boundaries are required
is an organizational decision rather than a universal one. Here it is required,
so it is expressed as code rather than as a sentence in a README that nothing
enforces.

Service-linked roles are exempt: AWS creates them with a fixed policy and
rejects a boundary on them, so requiring one would make the check unsatisfiable
and therefore ignored.
"""
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck


class RoleHasPermissionsBoundary(BaseResourceCheck):
    def __init__(self) -> None:
        super().__init__(
            name="IAM roles must be created with a permissions boundary",
            id="CKV_CAC_2",
            categories=[CheckCategories.IAM],
            supported_resources=["aws_iam_role"],
        )

    def scan_resource_conf(self, conf) -> CheckResult:
        name = conf.get("name", [""])
        name = name[0] if isinstance(name, list) and name else name
        if isinstance(name, str) and name.startswith("AWSServiceRoleFor"):
            return CheckResult.PASSED

        boundary = conf.get("permissions_boundary")
        if isinstance(boundary, list):
            boundary = boundary[0] if boundary else None
        if boundary in (None, "", "null"):
            return CheckResult.FAILED
        return CheckResult.PASSED


check = RoleHasPermissionsBoundary()
