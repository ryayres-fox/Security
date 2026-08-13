"""CLI tests.

These run the exact commands the README documents. A README that drifts from the
tool it documents is the same failure mode as a control that reports clean while
enforcing nothing — it passes inspection and delivers nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from findings_normalizer.cli import main

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _state(tmp_path) -> str:
    return str(tmp_path / "store.json")


def test_readme_quickstart_runs_end_to_end(tmp_path, capsys):
    st = _state(tmp_path)
    out = tmp_path / "report.html"

    assert main(["--state", st, "ingest", "--tool", "trivy",
                 "--input", str(SAMPLES / "trivy.json")]) == 0
    assert main(["--state", st, "ingest", "--tool", "semgrep",
                 "--input", str(SAMPLES / "semgrep.json")]) == 0
    assert main(["--state", st, "report", "--format", "html", "--out", str(out)]) == 0

    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "CVE-2023-45853" in html
    # Self-contained: no external asset can be fetched from a locked-down network.
    for marker in ("http://", "https://", "<script"):
        assert marker not in html, f"report must not reference {marker}"


def test_gate_exits_nonzero_when_blocking_findings_are_active(tmp_path):
    st = _state(tmp_path)
    main(["--state", st, "ingest", "--tool", "trivy", "--input", str(SAMPLES / "trivy.json")])
    assert main(["--state", st, "gate", "--fail-on", "critical,high"]) == 1
    assert main(["--state", st, "gate", "--fail-on", "info"]) == 0


def test_state_accumulates_across_separate_invocations(tmp_path):
    """Each CLI call is its own process in CI. State has to survive that."""
    st = _state(tmp_path)
    main(["--state", st, "ingest", "--tool", "tfsec", "--input", str(SAMPLES / "tfsec.json")])
    after_one = len(json.loads(Path(st).read_text())["findings"])
    main(["--state", st, "ingest", "--tool", "bandit", "--input", str(SAMPLES / "bandit.json")])
    after_two = len(json.loads(Path(st).read_text())["findings"])
    assert after_two > after_one


def test_cross_tool_merge_is_visible_in_the_cli_summary(tmp_path, capsys):
    st = _state(tmp_path)
    main(["--state", st, "ingest", "--tool", "tfsec", "--input", str(SAMPLES / "tfsec.json")])
    main(["--state", st, "ingest", "--tool", "trivy", "--input", str(SAMPLES / "trivy.json")])
    captured = capsys.readouterr().out
    assert "merged into existing" in captured

    main(["--state", st, "summary"])
    summary = json.loads(capsys.readouterr().out)
    assert summary["total_findings"] < 6, "tfsec+trivy overlap must fold"


def test_json_report_carries_history_fields(tmp_path, capsys):
    st = _state(tmp_path)
    main(["--state", st, "ingest", "--tool", "gitleaks",
          "--input", str(SAMPLES / "gitleaks.json"), "--scan-date", "2026-05-01"])
    capsys.readouterr()  # discard the ingest line; the report must parse alone
    main(["--state", st, "report", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["first_seen"] == "2026-05-01"
    assert "age_days" in payload["findings"][0]
    assert payload["summary"]["scan_dates"] == ["2026-05-01"]


def test_missing_input_file_fails_loudly(tmp_path):
    with pytest.raises(SystemExit, match="input not found"):
        main(["--state", _state(tmp_path), "ingest", "--tool", "trivy",
              "--input", str(tmp_path / "absent.json")])


def test_malformed_json_names_the_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit, match="not valid JSON"):
        main(["--state", _state(tmp_path), "ingest", "--tool", "trivy", "--input", str(bad)])


def test_unknown_severity_in_fail_on_is_rejected(tmp_path):
    """`--fail-on hihg` must not silently become a gate that blocks nothing."""
    st = _state(tmp_path)
    main(["--state", st, "ingest", "--tool", "trivy", "--input", str(SAMPLES / "trivy.json")])
    with pytest.raises(SystemExit, match="unknown severity"):
        main(["--state", st, "gate", "--fail-on", "hihg"])
