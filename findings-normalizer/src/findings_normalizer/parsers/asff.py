"""AWS Security Hub ASFF -> Finding.

ASFF is the one input that arrives with control IDs already attached, in
`Compliance.RelatedRequirements` — strings like "NIST.800-53.r5 AC-6". Those are
carried through verbatim after normalization, because a control mapping that
came from the source beats one inferred downstream.

Findings already archived or resolved in Security Hub are skipped. Re-ingesting
them would resurrect work someone has already closed, which is the fastest way
to make a normalizer distrusted.
"""
from __future__ import annotations

import re

from ..models import Finding, Location, Severity

_CONTROL = re.compile(r"([A-Z]{2}-\d+(?:\(\d+\))?)")


def _control_ids(compliance: dict) -> list[str]:
    out: list[str] = []
    for req in compliance.get("RelatedRequirements", []) or []:
        out.extend(_CONTROL.findall(req))
    return sorted(set(out))


def parse(raw: dict) -> list[Finding]:
    out: list[Finding] = []
    for f in raw.get("Findings", []) or []:
        workflow = (f.get("Workflow") or {}).get("Status", "NEW")
        record_state = f.get("RecordState", "ACTIVE")
        if workflow in {"RESOLVED", "SUPPRESSED"} or record_state == "ARCHIVED":
            continue

        resources = f.get("Resources") or []
        compliance = f.get("Compliance") or {}
        product = (f.get("ProductFields") or {}).get("aws/securityhub/ProductName", "")

        out.append(
            Finding(
                tool=f"securityhub:{product}" if product else "securityhub",
                tool_class="posture",
                # GeneratorId is stable across findings for the same control;
                # Id is per-resource and would defeat dedupe.
                rule_id=f.get("GeneratorId") or f.get("Id", "unknown"),
                title=(f.get("Title") or "")[:200],
                severity=Severity.parse((f.get("Severity") or {}).get("Label")),
                location=Location(
                    file_path=None,
                    resource_id=resources[0].get("Id") if resources else None,
                ),
                control_ids=_control_ids(compliance),
            )
        )
    return out
