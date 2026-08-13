"""CKV_CAC_3 — OIDC trust policies must not wildcard the subject claim.

The common form of a CI trust policy is `StringLike` on `sub` with a trailing
wildcard: `repo:org/repo:*`. That trusts every ref in the repository — every
branch, every tag, and on many configurations every pull request, including one
opened from a fork. The role is scoped, the boundary is attached, the policy
reads correctly in review, and anyone who can create a branch can assume it.

No built-in check covers this, and it is one of the highest-consequence
misconfigurations in a modern deployment pipeline, because the credential it
exposes has no expiry a scanner can see and leaves no artifact to find.

Detects both the wildcard and the weaker `StringLike` operator on a `:sub`
condition, since `StringLike` without a wildcard is an accident waiting to
become one.
"""
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.data.base_check import BaseDataCheck


class OidcSubjectNotWildcarded(BaseDataCheck):
    def __init__(self) -> None:
        super().__init__(
            name="OIDC trust policy must match the sub claim exactly, without wildcards",
            id="CKV_CAC_3",
            categories=[CheckCategories.IAM],
            supported_data=["aws_iam_policy_document"],
        )

    def scan_data_conf(self, conf) -> CheckResult:
        for statement in conf.get("statement", []) or []:
            if not isinstance(statement, dict):
                continue
            if not self._is_web_identity(statement):
                continue
            for condition in statement.get("condition", []) or []:
                if not isinstance(condition, dict):
                    continue
                if self._condition_is_unsafe(condition):
                    return CheckResult.FAILED
        return CheckResult.PASSED

    @staticmethod
    def _is_web_identity(statement: dict) -> bool:
        actions = statement.get("actions", [])
        flat = []
        for a in actions:
            flat.extend(a if isinstance(a, list) else [a])
        return any("AssumeRoleWithWebIdentity" in str(a) for a in flat)

    @staticmethod
    def _condition_is_unsafe(condition: dict) -> bool:
        variable = condition.get("variable")
        if isinstance(variable, list):
            variable = variable[0] if variable else ""
        if not str(variable).endswith(":sub"):
            return False

        test = condition.get("test")
        if isinstance(test, list):
            test = test[0] if test else ""
        if str(test) != "StringEquals":
            return True  # StringLike, ForAnyValue:StringLike, etc.

        values = condition.get("values", [])
        flat = []
        for v in values:
            flat.extend(v if isinstance(v, list) else [v])
        return any("*" in str(v) or "?" in str(v) for v in flat)


check = OidcSubjectNotWildcarded()
