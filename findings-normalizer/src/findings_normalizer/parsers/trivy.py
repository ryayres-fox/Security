"""Trivy JSON -> Finding."""
from __future__ import annotations

from ..models import Finding, Location, Severity

_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "UNKNOWN": Severity.INFO,
}


def parse(raw: dict) -> list[Finding]:
    out: list[Finding] = []
    for result in raw.get("Results", []):
        target = result.get("Target")
        for v in result.get("Vulnerabilities", []) or []:
            out.append(
                Finding(
                    tool="trivy",
                    tool_class="container",
                    rule_id=v.get("VulnerabilityID", "unknown"),
                    title=(v.get("Title") or v.get("VulnerabilityID", ""))[:200],
                    severity=_SEVERITY.get(v.get("Severity", "UNKNOWN"), Severity.INFO),
                    location=Location(file_path=target, resource_id=v.get("PkgName")),
                )
            )
        for m in result.get("Misconfigurations", []) or []:
            out.append(
                Finding(
                    tool="trivy",
                    tool_class="iac",
                    rule_id=m.get("ID", "unknown"),
                    title=(m.get("Title") or "")[:200],
                    severity=_SEVERITY.get(m.get("Severity", "UNKNOWN"), Severity.INFO),
                    location=Location(file_path=target, resource_id=m.get("Resolution")),
                )
            )
    return out
