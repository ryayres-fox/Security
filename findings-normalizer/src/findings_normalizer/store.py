"""Append-only finding store with cross-tool merge."""
from __future__ import annotations

from collections import defaultdict

from .models import Disposition, Finding, Severity


class FindingStore:
    def __init__(self) -> None:
        self._by_id: dict[str, Finding] = {}

    def ingest(self, findings: list[Finding]) -> None:
        for f in findings:
            problems = f.validate()
            if problems:
                raise ValueError(f"{f.rule_id}: {'; '.join(problems)}")
            existing = self._by_id.get(f.finding_id)
            if existing is None:
                f.reported_by.add(f.tool)
                self._by_id[f.finding_id] = f
                continue
            # Same finding, another tool saw it. Keep the higher severity and
            # record the attribution — agreement across tools is signal.
            existing.reported_by.add(f.tool)
            if f.severity.rank > existing.severity.rank:
                existing.severity = f.severity
            existing.control_ids = sorted(set(existing.control_ids) | set(f.control_ids))

    @property
    def findings(self) -> list[Finding]:
        return list(self._by_id.values())

    def active(self) -> list[Finding]:
        return [f for f in self.findings if f.disposition is Disposition.ACTIVE]

    def counts_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for f in self.active():
            out[f.severity.value] += 1
        return dict(out)

    def gate(self, fail_on: list[Severity]) -> tuple[bool, list[Finding]]:
        """CI gate. Returns (passed, offending findings)."""
        blocking = [f for f in self.active() if f.severity in fail_on]
        return (not blocking, blocking)

    def triage_rate(self) -> float:
        total = len(self.findings)
        if not total:
            return 1.0
        return 1 - (len(self.active()) / total)
