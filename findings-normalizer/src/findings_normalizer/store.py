"""Append-only finding store with cross-tool merge.

The store keeps two things: an immutable observation log, and a folded view of
current state. Reports read the fold; questions about time read the log.

Why append-only matters in practice: a store that overwrites can tell you what
is broken today. It cannot tell you that a finding was fixed in April and came
back in July, which is the difference between a bug and a process failure.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .models import Disposition, Finding, Observation, Severity


class FindingStore:
    def __init__(self) -> None:
        self._by_id: dict[str, Finding] = {}
        self._log: list[Observation] = []

    # ---------------------------------------------------------------- ingest

    def ingest(self, findings: list[Finding], scan_date: date | None = None) -> None:
        scan_date = scan_date or date.today()
        for f in findings:
            problems = f.validate()
            if problems:
                raise ValueError(f"{f.rule_id}: {'; '.join(problems)}")

            self._log.append(
                Observation(
                    finding_id=f.finding_id,
                    tool=f.tool,
                    severity=f.severity,
                    scan_date=scan_date,
                    line=f.location.line,
                )
            )

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

    # ------------------------------------------------------------ current view

    @property
    def findings(self) -> list[Finding]:
        return list(self._by_id.values())

    @property
    def observations(self) -> list[Observation]:
        return list(self._log)

    def get(self, finding_id: str) -> Finding | None:
        return self._by_id.get(finding_id)

    def active(self, as_of: date | None = None) -> list[Finding]:
        """Active findings, counting lapsed risk acceptances as active again."""
        as_of = as_of or date.today()
        return [
            f
            for f in self.findings
            if f.disposition is Disposition.ACTIVE or f.is_expired(as_of)
        ]

    def expired_acceptances(self, as_of: date | None = None) -> list[Finding]:
        as_of = as_of or date.today()
        return [f for f in self.findings if f.is_expired(as_of)]

    def counts_by_severity(self, as_of: date | None = None) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for f in self.active(as_of):
            out[f.severity.value] += 1
        return dict(out)

    def counts_by_tool_class(self, as_of: date | None = None) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for f in self.active(as_of):
            out[f.tool_class] += 1
        return dict(out)

    def control_coverage(self) -> dict[str, int]:
        """Findings per referenced control ID — the input to a gap analysis."""
        out: dict[str, int] = defaultdict(int)
        for f in self.findings:
            for cid in f.control_ids:
                out[cid] += 1
        return dict(out)

    # ------------------------------------------------------------------- time

    def first_seen(self, finding_id: str) -> date | None:
        dates = [o.scan_date for o in self._log if o.finding_id == finding_id]
        return min(dates) if dates else None

    def last_seen(self, finding_id: str) -> date | None:
        dates = [o.scan_date for o in self._log if o.finding_id == finding_id]
        return max(dates) if dates else None

    def age_days(self, finding_id: str, as_of: date | None = None) -> int | None:
        first = self.first_seen(finding_id)
        if first is None:
            return None
        return ((as_of or date.today()) - first).days

    def scan_dates(self) -> list[date]:
        return sorted({o.scan_date for o in self._log})

    def is_regression(self, finding_id: str) -> bool:
        """True if the finding was absent for at least one scan and returned.

        Requires at least three scan dates to mean anything: seen, gone, back.
        """
        all_scans = self.scan_dates()
        seen_on = {o.scan_date for o in self._log if o.finding_id == finding_id}
        if not seen_on:
            return False
        window = [d for d in all_scans if d >= min(seen_on)]
        gap_then_return = False
        had_gap = False
        for d in window:
            if d not in seen_on:
                had_gap = True
            elif had_gap:
                gap_then_return = True
        return gap_then_return

    def regressions(self) -> list[Finding]:
        return [f for f in self.findings if self.is_regression(f.finding_id)]

    # ------------------------------------------------------------------- gate

    def gate(
        self, fail_on: list[Severity], as_of: date | None = None
    ) -> tuple[bool, list[Finding]]:
        """CI gate. Returns (passed, offending findings)."""
        blocking = [f for f in self.active(as_of) if f.severity in fail_on]
        return (not blocking, blocking)

    def triage_rate(self, as_of: date | None = None) -> float:
        total = len(self.findings)
        if not total:
            return 1.0
        return 1 - (len(self.active(as_of)) / total)

    # ---------------------------------------------------------- serialization

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "findings": [f.to_dict() for f in self.findings],
            "observations": [o.to_dict() for o in self._log],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FindingStore:
        store = cls()
        for fd in d.get("findings", []):
            f = Finding.from_dict(fd)
            store._by_id[f.finding_id] = f
        store._log = [Observation.from_dict(o) for o in d.get("observations", [])]
        return store

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> FindingStore:
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
