"""Gitleaks JSON -> Finding.

The secret value is never read out of the report and never enters a Finding.

That is not a stylistic choice. Gitleaks output contains the matched secret in
`Secret` and often the surrounding line in `Match`. A normalizer that copies
those fields into its own store has taken a credential that existed in one
place and written it to a second one — usually a JSON artifact, frequently
uploaded to CI, occasionally committed. The tool that finds the leak should not
be the tool that spreads it.

Identity uses the commit and the rule, not the secret, so rotating the
credential does not mint a new finding for the same exposure.
"""
from __future__ import annotations

from ..models import Finding, Location, Severity


def parse(raw: list | dict) -> list[Finding]:
    rows = raw if isinstance(raw, list) else (raw.get("findings") or [])
    out: list[Finding] = []
    for r in rows:
        commit = (r.get("Commit") or "")[:12]
        out.append(
            Finding(
                tool="gitleaks",
                tool_class="secrets",
                rule_id=r.get("RuleID", "unknown"),
                # Description only. Never r["Secret"], never r["Match"].
                title=(r.get("Description") or "detected secret")[:200],
                # A committed credential is exposed until it is rotated. There is
                # no "medium" version of that.
                severity=Severity.HIGH,
                location=Location(
                    file_path=r.get("File"),
                    resource_id=commit or None,
                    line=r.get("StartLine"),
                ),
                control_ids=["IA-5"],
            )
        )
    return out
