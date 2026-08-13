"""tfsec JSON -> Finding.

Identity uses `rule_id` (the AVD identifier), not `long_id`. tfsec and Trivy
draw from the same Aqua vulnerability database and agree on AVD-AWS-0107, but
tfsec additionally names it `aws-vpc-no-public-ingress-sgr` and Trivy does not.
Hashing the friendlier name splits one misconfiguration into two findings across
two tools that were never actually in disagreement. The vendor name is kept as
`native_rule_id` for display.
"""
from __future__ import annotations

from ..models import Finding, Location, Severity


def parse(raw: dict) -> list[Finding]:
    out: list[Finding] = []
    for r in raw.get("results", []) or []:
        loc = r.get("location") or {}
        out.append(
            Finding(
                tool="tfsec",
                tool_class="iac",
                rule_id=r.get("rule_id") or r.get("long_id") or "unknown",
                native_rule_id=r.get("long_id"),
                title=(r.get("description") or "")[:200],
                severity=Severity.parse(r.get("severity")),
                location=Location(
                    file_path=loc.get("filename"),
                    resource_id=r.get("resource"),
                    line=loc.get("start_line"),
                ),
            )
        )
    return out
