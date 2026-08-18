"""Tests for the coverage folder.

The script is a gate, so the tests that matter are the ones proving it *fails*
when it should. A checker that only ever passes is indistinguishable from no
checker at all, and it takes an incident to find out which one you have.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from control_coverage import (
    build_report,
    collect,
    main,
    parse_controls_yaml,
    to_markdown,
)

REPO = Path(__file__).resolve().parents[1]
GOOD = """\
module: example-module
implements:
  - id: AU-9
    statement: Audit information is protected from unauthorized modification
    evidence: log_file_validation asserted in tests
  - id: AC-6(5)
    statement: Least privilege for administrators
    evidence: permission boundary attached at creation

exceptions:
  - check: CKV_AWS_144
    resource: aws_s3_bucket.audit
    reason: replication is a caller-level availability decision
"""


def _write(tmp_path: Path, body: str, name: str = "mod-a") -> Path:
    root = tmp_path / "arch" / name
    root.mkdir(parents=True)
    (root / "main.tf").write_text('resource "null_resource" "x" {}\n', encoding="utf-8")
    if body is not None:
        (root / "controls.yaml").write_text(body, encoding="utf-8")
    return tmp_path / "arch"


# ------------------------------------------------------------------ parsing


def test_parses_the_documented_shape():
    data = parse_controls_yaml(GOOD)
    assert data["module"] == "example-module"
    assert [c["id"] for c in data["implements"]] == ["AU-9", "AC-6(5)"]
    assert data["implements"][0]["evidence"].startswith("log_file_validation")
    assert data["exceptions"][0]["check"] == "CKV_AWS_144"


def test_parser_raises_rather_than_skipping_what_it_cannot_read():
    """A lenient parser under-reports coverage, and under-reported coverage
    reads as success."""
    with pytest.raises(ValueError, match="unexpected top-level key"):
        parse_controls_yaml("module: m\nimplemnts:\n  - id: AU-9\n")

    with pytest.raises(ValueError, match="list item outside a known section"):
        parse_controls_yaml("  - id: AU-9\n")


def test_comments_and_blank_lines_are_ignored():
    data = parse_controls_yaml("# a note\n\nmodule: m\nimplements:\n  - id: AU-2\n")
    assert data["module"] == "m"
    assert data["implements"][0]["id"] == "AU-2"


# ----------------------------------------------------------------- checking


def test_module_without_controls_yaml_is_a_problem(tmp_path):
    root = _write(tmp_path, None)
    modules, problems = collect(root)
    assert modules == []
    assert any("no controls.yaml" in p for p in problems)


def test_control_without_evidence_is_a_problem(tmp_path):
    """'We implement AU-9' is an assertion. Evidence is what makes it a control."""
    root = _write(tmp_path, "module: m\nimplements:\n  - id: AU-9\n    statement: things\n")
    _, problems = collect(root)
    assert any("missing evidence" in p for p in problems)


def test_malformed_control_id_is_caught(tmp_path):
    """A typo'd ID produces a control nobody implements and nobody misses."""
    body = "module: m\nimplements:\n  - id: AU9\n    statement: s\n    evidence: e\n"
    root = _write(tmp_path, body)
    _, problems = collect(root)
    assert any("not a well-formed" in p for p in problems)


def test_unknown_control_family_is_caught(tmp_path):
    body = "module: m\nimplements:\n  - id: ZZ-9\n    statement: s\n    evidence: e\n"
    root = _write(tmp_path, body)
    _, problems = collect(root)
    assert any("unknown control family" in p for p in problems)


def test_exception_without_a_reason_is_a_problem(tmp_path):
    """An exception you can't read and argue with is a gap wearing a comment."""
    root = _write(
        tmp_path,
        "module: m\nimplements:\n  - id: AU-9\n    statement: s\n    evidence: e\n"
        "exceptions:\n  - check: CKV_AWS_1\n    resource: r\n",
    )
    _, problems = collect(root)
    assert any("missing reason" in p for p in problems)


def test_a_valid_module_produces_no_problems(tmp_path):
    root = _write(tmp_path, GOOD)
    modules, problems = collect(root)
    assert problems == []
    assert modules[0]["name"] == "example-module"


# --------------------------------------------------------------- components


def test_a_component_is_collected_alongside_modules(tmp_path):
    """A non-Terraform component (the scanning pipeline) declares controls the
    same way, and does not need a .tf file to be counted."""
    root = _write(tmp_path, GOOD)
    comp = tmp_path / "pipeline" / "controls.yaml"
    comp.parent.mkdir(parents=True)
    comp.write_text(
        "module: security-pipeline\nimplements:\n  - id: RA-5\n"
        "    statement: scanners run on every change\n    evidence: ci.yml required checks\n",
        encoding="utf-8",
    )
    units, problems = collect(root, (str(comp),))
    assert problems == []
    names = {u["name"] for u in units}
    assert names == {"example-module", "security-pipeline"}


def test_a_component_is_held_to_the_same_evidence_rule(tmp_path):
    """The pipeline is not exempt: a control with no evidence is still a problem."""
    root = _write(tmp_path, GOOD)
    comp = tmp_path / "pipeline" / "controls.yaml"
    comp.parent.mkdir(parents=True)
    comp.write_text(
        "module: security-pipeline\nimplements:\n  - id: RA-5\n    statement: scanners run\n",
        encoding="utf-8",
    )
    _, problems = collect(root, (str(comp),))
    assert any("missing evidence" in p for p in problems)


def test_the_real_scanning_pipeline_component_is_valid(capsys):
    """The repo's own .github/controls.yaml has to pass the same gate."""
    rc = main([
        "--root", str(REPO / "reference-architecture"),
        "--component", str(REPO / ".github" / "controls.yaml"),
        "--check",
    ])
    assert rc == 0
    assert "check passed" in capsys.readouterr().out


# ------------------------------------------------------------------ reports


def test_report_groups_by_family_and_counts_distinct_controls(tmp_path):
    root = _write(tmp_path, GOOD)
    modules, _ = collect(root)
    report = build_report(modules)
    assert report["families_covered"] == ["AC", "AU"]
    assert report["distinct_controls"] == 2
    assert report["exceptions"] == 1
    assert report["by_family"]["AU"]["AU-9"] == ["example-module"]


def test_markdown_names_the_evidence_and_the_exceptions(tmp_path):
    root = _write(tmp_path, GOOD)
    modules, _ = collect(root)
    md = to_markdown(modules, build_report(modules))
    assert "Audit & Accountability" in md
    assert "log_file_validation asserted in tests" in md
    assert "CKV_AWS_144" in md
    assert "does not claim any control" in md, "the implemented-vs-satisfied caveat must survive"


# ----------------------------------------------------- against the real repo


def test_the_actual_reference_architecture_passes_its_own_check(capsys):
    """The repo has to pass its own gate. That is the entire premise."""
    assert main(["--root", str(REPO / "reference-architecture"), "--check"]) == 0
    assert "check passed" in capsys.readouterr().out


def test_check_mode_exits_nonzero_on_a_broken_tree(tmp_path):
    root = _write(tmp_path, None)
    assert main(["--root", str(root), "--check"]) == 1


def test_missing_root_is_an_argument_error(tmp_path):
    assert main(["--root", str(tmp_path / "nope"), "--check"]) == 2
