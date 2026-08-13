"""Semgrep JSON -> Finding."""
from __future__ import annotations

from ..models import Finding, Location, Severity

_SEVERITY = {"ERROR": Severity.HIGH, "WARNING": Severity.MEDIUM, "INFO": Severity.LOW}


def parse(raw: dict) -> list[Finding]:
    out: list[Finding] = []
    for r in raw.get("results", []):
        extra = r.get("extra", {})
        meta = extra.get("metadata", {})
        out.append(
            Finding(
                tool="semgrep",
                tool_class="sast",
                rule_id=r.get("check_id", "unknown"),
                title=extra.get("message", "").strip()[:200],
                severity=_SEVERITY.get(extra.get("severity", "INFO"), Severity.LOW),
                location=Location(
                    file_path=r.get("path"),
                    line=(r.get("start") or {}).get("line"),
                ),
                control_ids=list(meta.get("nist-800-53", []) or []),
            )
        )
    return out
