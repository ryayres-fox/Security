"""Tests for the properties an append-only store exists to provide.

If these pass against an overwriting store, the append-only design is not
earning its complexity. They do not.
"""
from __future__ import annotations

from datetime import date

from findings_normalizer.models import Disposition, Finding, Location, Severity
from findings_normalizer.store import FindingStore

D1, D2, D3, D4 = (date(2026, 5, i) for i in (1, 2, 3, 4))


def _f(rule_id="r1", **kw):
    base = dict(
        tool="semgrep",
        tool_class="sast",
        rule_id=rule_id,
        title="t",
        severity=Severity.HIGH,
        location=Location(file_path="a.py"),
    )
    base.update(kw)
    return Finding(**base)


def test_first_seen_survives_later_scans():
    s = FindingStore()
    s.ingest([_f()], scan_date=D1)
    s.ingest([_f()], scan_date=D3)
    fid = _f().finding_id
    assert s.first_seen(fid) == D1
    assert s.last_seen(fid) == D3
    assert s.age_days(fid, as_of=D4) == 3


def test_regression_detected_when_a_finding_returns_after_a_clean_scan():
    """Fixed in one scan, back in the next. The single question an overwriting
    store cannot answer, and the one that distinguishes a bug from a process
    failure."""
    s = FindingStore()
    s.ingest([_f("returns")], scan_date=D1)
    s.ingest([_f("other")], scan_date=D2)      # 'returns' absent — fixed
    s.ingest([_f("returns")], scan_date=D3)    # and it's back

    assert s.is_regression(_f("returns").finding_id) is True
    assert s.is_regression(_f("other").finding_id) is False
    assert [f.rule_id for f in s.regressions()] == ["returns"]


def test_a_finding_present_in_every_scan_is_not_a_regression():
    s = FindingStore()
    for d in (D1, D2, D3):
        s.ingest([_f("persistent")], scan_date=d)
    assert s.is_regression(_f("persistent").finding_id) is False


def test_a_finding_first_seen_late_is_not_a_regression():
    """New findings must not be misread as returning ones just because earlier
    scans exist."""
    s = FindingStore()
    s.ingest([_f("early")], scan_date=D1)
    s.ingest([_f("early")], scan_date=D2)
    s.ingest([_f("late")], scan_date=D3)
    assert s.is_regression(_f("late").finding_id) is False


def test_expired_risk_acceptance_becomes_active_again():
    """An acceptance with an expiry that nobody enforces is a permanent waiver
    wearing a deadline."""
    s = FindingStore()
    s.ingest(
        [
            _f(
                disposition=Disposition.ACCEPTED,
                owner="platform-team",
                compensating_control="WAF rule blocks the path externally",
                expires_on=D2,
                severity=Severity.CRITICAL,
            )
        ],
        scan_date=D1,
    )
    assert s.active(as_of=D1) == []
    assert len(s.active(as_of=D4)) == 1
    assert len(s.expired_acceptances(as_of=D4)) == 1

    passed_before, _ = s.gate([Severity.CRITICAL], as_of=D1)
    passed_after, blocking = s.gate([Severity.CRITICAL], as_of=D4)
    assert passed_before is True
    assert passed_after is False and len(blocking) == 1


def test_round_trip_through_disk_preserves_history_and_dispositions(tmp_path):
    """ingest and gate are separate CI steps in separate processes. If state does
    not survive serialization, the tool works in tests and fails in the pipeline."""
    s = FindingStore()
    s.ingest([_f("returns")], scan_date=D1)
    s.ingest([_f("other")], scan_date=D2)
    s.ingest([_f("returns")], scan_date=D3)

    path = tmp_path / "store.json"
    s.save(path)
    loaded = FindingStore.load(path)

    assert len(loaded.findings) == len(s.findings)
    assert len(loaded.observations) == 3
    assert loaded.first_seen(_f("returns").finding_id) == D1
    assert loaded.is_regression(_f("returns").finding_id) is True


def test_loading_a_missing_state_file_yields_an_empty_store(tmp_path):
    """First CI run has no prior state. That is not an error condition."""
    s = FindingStore.load(tmp_path / "nope.json")
    assert s.findings == [] and s.triage_rate() == 1.0


def test_unknown_tool_class_is_rejected_at_ingest():
    """tool_class is part of the identity hash. A typo'd class silently mints a
    parallel universe of duplicate findings."""
    s = FindingStore()
    try:
        s.ingest([_f(tool_class="statik")])
    except ValueError as e:
        assert "tool_class" in str(e)
    else:
        raise AssertionError("expected an unknown tool_class to be rejected")


def test_control_coverage_counts_findings_per_control():
    s = FindingStore()
    s.ingest([
        _f("a", control_ids=["AC-6"]),
        _f("b", control_ids=["AC-6", "SC-7"]),
    ])
    assert s.control_coverage() == {"AC-6": 2, "SC-7": 1}
