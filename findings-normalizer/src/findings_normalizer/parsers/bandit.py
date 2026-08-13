"""Bandit JSON -> Finding.

Bandit reports both a severity and a confidence. Only severity is carried into
the record: confidence describes how sure the tool is, which is a triage input,
not a property of the risk. Folding it into severity conflates two questions.
"""
from __future__ import annotations

from ..models import Finding, Location, Severity


def parse(raw: dict) -> list[Finding]:
    out: list[Finding] = []
    for r in raw.get("results", []) or []:
        cwe = r.get("issue_cwe") or {}
        out.append(
            Finding(
                tool="bandit",
                tool_class="sast",
                rule_id=r.get("test_id", "unknown"),
                title=(r.get("issue_text") or "")[:200],
                severity=Severity.parse(r.get("issue_severity")),
                location=Location(
                    file_path=r.get("filename"),
                    resource_id=r.get("test_name"),
                    line=r.get("line_number"),
                ),
                control_ids=[f"CWE-{cwe['id']}"] if cwe.get("id") else [],
            )
        )
    return out
