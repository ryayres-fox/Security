"""Checkov JSON -> Finding.

Two shapes in the wild: a single object, or a list of objects when more than one
framework ran in the same invocation. Handling only the first is the usual bug,
and it fails silently — you get zero findings and a green build.
"""
from __future__ import annotations

from ..models import Finding, Location, Severity


def _results(raw: dict | list) -> list[dict]:
    blocks = raw if isinstance(raw, list) else [raw]
    out: list[dict] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        out.extend((b.get("results") or {}).get("failed_checks", []) or [])
    return out


def parse(raw: dict | list) -> list[Finding]:
    out: list[Finding] = []
    for c in _results(raw):
        out.append(
            Finding(
                tool="checkov",
                tool_class="iac",
                rule_id=c.get("check_id", "unknown"),
                title=(c.get("check_name") or c.get("check_id") or "")[:200],
                # Community Checkov leaves severity null; a missing severity is
                # not an absent risk, so it lands at MEDIUM rather than INFO.
                severity=Severity.parse(c.get("severity"), default=Severity.MEDIUM),
                location=Location(
                    file_path=c.get("file_path"),
                    resource_id=c.get("resource"),
                    line=((c.get("file_line_range") or [None])[0]),
                ),
                # Checkov emits no control IDs. The module -> control mapping
                # lives in each module's controls.yaml and is applied downstream.
                # Inferring one from a guideline URL would be a guess wearing the
                # costume of a citation.
                control_ids=[],
            )
        )
    return out
