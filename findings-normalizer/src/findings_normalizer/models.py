"""Core record types.

Design note: identity is deliberately NOT derived from line numbers or scan
timestamps. A finding that moves down a file when someone adds an import is the
same finding; treating it as new is how a backlog becomes noise nobody reads.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[self.value]


class Disposition(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"           # requires owner + compensating control + expiry
    FALSE_POSITIVE = "false_positive"  # requires a reason


@dataclass(frozen=True)
class Location:
    file_path: str | None = None
    resource_id: str | None = None
    line: int | None = None  # captured for humans; deliberately excluded from identity


@dataclass
class Finding:
    tool: str
    tool_class: str          # sast | iac | container | secrets | dependency | posture
    rule_id: str
    title: str
    severity: Severity
    location: Location
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
