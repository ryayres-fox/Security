from datetime import date

import pytest

from findings_normalizer.models import Disposition, Finding, Location, Severity
from findings_normalizer.parsers import semgrep, trivy
from findings_normalizer.store import FindingStore


def _f(**kw):
    base = dict(tool="semgrep", tool_class="sast", rule_id="r1", title="t",
                severity=Severity.HIGH, location=Location(file_path="a.py"))
    base.update(kw)
    return Finding(**base)


def test_identity_is_stable_across_line_movement():
    a = _f(location=Location(file_path="a.py", line=10))
    b = _f(location=Location(file_path="a.py", line=93))
    assert a.finding_id == b.finding_id, "line drift must not mint a new finding"


def test_same_issue_from_two_tools_merges_and_keeps_attribution():
    s = FindingStore()
    s.ingest([_f(tool="semgrep", severity=Severity.MEDIUM)])
    s.ingest([_f(tool="bandit", severity=Severity.CRITICAL)])
    assert len(s.findings) == 1
    only = s.findings[0]
    assert only.reported_by == {"semgrep", "bandit"}
    assert only.severity is Severity.CRITICAL, "merge keeps the higher severity"


def test_accepted_finding_requires_owner_control_and_expiry():
    s = FindingStore()
    with pytest.raises(ValueError):
        s.ingest([_f(disposition=Disposition.ACCEPTED)])
    s.ingest([_f(disposition=Disposition.ACCEPTED, owner="ryan",
                 compensating_control="WAF rule 12", expires_on=date(2026, 12, 31))])
    assert len(s.findings) == 1


def test_false_positive_requires_a_reason():
    s = FindingStore()
    with pytest.raises(ValueError):
        s.ingest([_f(disposition=Disposition.FALSE_POSITIVE)])


def test_gate_blocks_on_configured_severities():
    s = FindingStore()
    s.ingest([_f(rule_id="crit", severity=Severity.CRITICAL),
              _f(rule_id="low", severity=Severity.LOW)])
    passed, blocking = s.gate([Severity.CRITICAL, Severity.HIGH])
    assert not passed and len(blocking) == 1


def test_triage_rate_counts_non_active_dispositions():
    s = FindingStore()
    s.ingest([_f(rule_id="a", disposition=Disposition.RESOLVED),
              _f(rule_id="b", disposition=Disposition.ACTIVE)])
    assert s.triage_rate() == 0.5


def test_semgrep_parser_maps_severity_and_controls():
    raw = {"results": [{"check_id": "py.auth.missing", "path": "app/api.py",
                        "start": {"line": 12},
                        "extra": {"message": "missing authz", "severity": "ERROR",
                                  "metadata": {"nist-800-53": ["AC-3"]}}}]}
    out = semgrep.parse(raw)
    assert out[0].severity is Severity.HIGH and out[0].control_ids == ["AC-3"]


def test_trivy_parser_splits_vulns_and_misconfigs_by_tool_class():
    raw = {"Results": [{"Target": "img:latest",
                        "Vulnerabilities": [{"VulnerabilityID": "CVE-1", "Severity": "CRITICAL",
                                             "PkgName": "openssl"}],
                        "Misconfigurations": [{"ID": "AVD-AWS-1", "Severity": "MEDIUM",
                                               "Title": "public bucket"}]}]}
    out = trivy.parse(raw)
    assert {f.tool_class for f in out} == {"container", "iac"}
