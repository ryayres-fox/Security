"""Core record types.

Design note: identity is deliberately NOT derived from line numbers or scan
timestamps. A finding that moves down a file when someone adds an import is the
same finding; treating it as new is how a backlog becomes noise nobody reads.

Second design note: an `Observation` is what a scanner saw on one day. A
`Finding` is the folded current state. Keeping them separate is what makes
"when did this first appear?" and "did it come back?" answerable at all — a
store that overwrites on each scan can answer neither, and you don't discover
that until the first time someone asks.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

TOOL_CLASSES = frozenset(
    {"sast", "iac", "container", "secrets", "dependency", "posture"}
)


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[self.value]

    @classmethod
    def parse(cls, raw: str | None, default: Severity = None) -> Severity:
        """Tolerant lookup. Scanners disagree on case and on vocabulary."""
        if raw is None:
            return default or cls.INFO
        key = str(raw).strip().lower()
        aliases = {
            "error": cls.HIGH,
            "warning": cls.MEDIUM,
            "warn": cls.MEDIUM,
            "note": cls.LOW,
            "informational": cls.INFO,
            "unknown": cls.INFO,
            "none": cls.INFO,
            "moderate": cls.MEDIUM,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError:
            return default or cls.INFO


class Disposition(StrEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"              # requires owner + compensating control + expiry
    FALSE_POSITIVE = "false_positive"  # requires a reason


@dataclass(frozen=True)
class Location:
    file_path: str | None = None
    resource_id: str | None = None
    line: int | None = None  # captured for humans; deliberately excluded from identity


@dataclass(frozen=True)
class Observation:
    """One scanner's sighting of one finding on one day. Never mutated."""

    finding_id: str
    tool: str
    severity: Severity
    scan_date: date
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "tool": self.tool,
            "severity": self.severity.value,
            "scan_date": self.scan_date.isoformat(),
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Observation:
        return cls(
            finding_id=d["finding_id"],
            tool=d["tool"],
            severity=Severity(d["severity"]),
            scan_date=date.fromisoformat(d["scan_date"]),
            line=d.get("line"),
        )


@dataclass
class Finding:
    tool: str
    tool_class: str          # sast | iac | container | secrets | dependency | posture
    rule_id: str             # the SHARED identifier where one exists (e.g. AVD-AWS-0107)
    title: str
    severity: Severity
    location: Location
    # The vendor's own name for the rule. Kept for humans, excluded from identity
    # for the same reason line numbers are: it is a label, not the thing itself.
    # tfsec calls AVD-AWS-0107 "aws-vpc-no-public-ingress-sgr"; Trivy does not.
    # Letting either name into the hash means the same misconfiguration, reported
    # by two tools that literally share a rule database, becomes two findings.
    native_rule_id: str | None = None
    control_ids: list[str] = field(default_factory=list)  # e.g. ["AC-6", "SC-13"]
    disposition: Disposition = Disposition.ACTIVE
    owner: str | None = None
    compensating_control: str | None = None
    expires_on: date | None = None
    false_positive_reason: str | None = None
    reported_by: set[str] = field(default_factory=set)

    @property
    def finding_id(self) -> str:
        basis = "|".join([
            self.tool_class,
            self.rule_id,
            self.location.file_path or "",
            self.location.resource_id or "",
        ])
        return hashlib.sha256(basis.encode()).hexdigest()[:16]

    def validate(self) -> list[str]:
        """Disposition rules the store refuses to accept without."""
        problems: list[str] = []
        if self.tool_class not in TOOL_CLASSES:
            problems.append(
                f"unknown tool_class {self.tool_class!r}; identity would be unstable"
            )
        if self.disposition is Disposition.ACCEPTED:
            if not self.owner:
                problems.append("accepted finding requires an owner")
            if not self.compensating_control:
                problems.append("accepted finding requires a compensating control")
            if not self.expires_on:
                problems.append("accepted finding requires an expiry date")
        if self.disposition is Disposition.FALSE_POSITIVE and not self.false_positive_reason:
            problems.append("false positive requires a reason")
        return problems

    def is_expired(self, as_of: date) -> bool:
        """An accepted risk past its expiry is an active finding again.

        This is the whole point of requiring an expiry: acceptance is a decision
        with a shelf life, not a way to close a ticket permanently.
        """
        return (
            self.disposition is Disposition.ACCEPTED
            and self.expires_on is not None
            and self.expires_on < as_of
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["disposition"] = self.disposition.value
        d["expires_on"] = self.expires_on.isoformat() if self.expires_on else None
        d["reported_by"] = sorted(self.reported_by)
        d["finding_id"] = self.finding_id
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        return cls(
            tool=d["tool"],
            tool_class=d["tool_class"],
            rule_id=d["rule_id"],
            title=d["title"],
            severity=Severity(d["severity"]),
            location=Location(**d["location"]),
            native_rule_id=d.get("native_rule_id"),
            control_ids=list(d.get("control_ids") or []),
            disposition=Disposition(d.get("disposition", "active")),
            owner=d.get("owner"),
            compensating_control=d.get("compensating_control"),
            expires_on=date.fromisoformat(d["expires_on"]) if d.get("expires_on") else None,
            false_positive_reason=d.get("false_positive_reason"),
            reported_by=set(d.get("reported_by") or []),
        )
