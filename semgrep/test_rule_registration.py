"""Prove the custom Semgrep rule set loads AND fires.

Same two assertions as `policies/`, for the same reason. A rule set can fail in
two directions and only one of them is visible:

  1. **It never loads.** A `--config` path that resolves to nothing, a YAML
     parse error swallowed by a wrapper script, a rules directory that moved.
     Semgrep scans, reports its findings from whatever *did* load, and exits 0.

  2. **It loads and never matches.** A pattern that was correct against the code
     as it looked when written, and silently stopped matching after a refactor —
     a decorator renamed, a framework upgraded, `requests` swapped for `httpx`.
     The rule is present, registered, and inert.

Either alone is a fail-open, and both produce the same output as a clean scan:
no findings. So both are asserted, plus a third thing almost nothing checks —
that the rules do **not** fire on the compliant fixture. A rule set that flags
correct code gets suppressed within a week, and a suppressed rule reports
success forever after.

That third assertion already earned its place: `reference-tenant-scope-from-
request` originally matched `request.state.auth.tenant_id`, which is the
*correct* way to obtain a tenant. The compliant fixture caught the rule flagging
the right answer as loudly as the wrong one.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RULES = HERE / "rules"
NONCOMPLIANT = HERE / "fixtures" / "noncompliant"
COMPLIANT = HERE / "fixtures" / "compliant"

RULE_ID = re.compile(r"^\s*-\s*id:\s*(\S+)", re.MULTILINE)


def _declared_rule_ids() -> set[str]:
    """Read from source rather than hardcoded.

    A hardcoded list keeps passing when a rule is added and fails to load, which
    is the exact defect this file exists to catch.
    """
    ids: set[str] = set()
    for path in RULES.glob("*.yml"):
        ids |= set(RULE_ID.findall(path.read_text(encoding="utf-8")))
    return ids


DECLARED = _declared_rule_ids()

pytestmark = pytest.mark.skipif(
    shutil.which("semgrep") is None,
    reason="semgrep CLI not installed — the CI semgrep job installs it explicitly",
)


def _run(target: Path) -> tuple[Counter, dict]:
    """Return (findings by short rule id, raw payload)."""
    proc = subprocess.run(
        ["semgrep", "--config", str(RULES), "--json", "--quiet",
         "--disable-version-check", str(target)],
        capture_output=True, text=True,
    )
    if not proc.stdout.strip():
        raise AssertionError(f"semgrep produced no output; stderr:\n{proc.stderr[:2000]}")
    payload = json.loads(proc.stdout)
    counts = Counter(r["check_id"].split(".")[-1] for r in payload.get("results", []))
    return counts, payload


# ---------------------------------------------------------------- sanity


def test_rules_are_declared_at_all():
    """Guards every other test here.

    If the ID regex stops matching, DECLARED empties and the parametrized tests
    below silently collect zero cases and report success.
    """
    assert DECLARED, "no rule IDs found; the rest of this suite would be vacuous"
    assert len(DECLARED) >= 6


def test_no_rule_failed_to_parse():
    """A YAML error in one file does not stop the others loading.

    Semgrep reports the broken file as an error and scans with what remains —
    so a rule set can be half-loaded while the scan looks entirely normal.
    """
    _, payload = _run(NONCOMPLIANT)
    errors = payload.get("errors", [])
    assert not errors, f"semgrep reported rule errors: {errors}"


# ------------------------------------------------- assertion 1: they load


def test_every_declared_rule_is_loaded():
    _, payload = _run(NONCOMPLIANT)
    scanned = payload.get("paths", {}).get("scanned", [])
    assert scanned, "semgrep scanned no files — the config path is wrong"

    proc = subprocess.run(
        ["semgrep", "--config", str(RULES), "--validate", "--quiet",
         "--disable-version-check"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"rule validation failed:\n{proc.stdout}{proc.stderr}"


# ------------------------------------------------- assertion 2: they fire


@pytest.mark.parametrize("rule_id", sorted(DECLARED))
def test_rule_fires_on_the_noncompliant_fixture(rule_id):
    """Loading is not enforcement. Each rule must actually match something."""
    counts, _ = _run(NONCOMPLIANT)
    assert counts.get(rule_id, 0) > 0, (
        f"{rule_id} is declared and matched nothing. A rule that loads and never "
        f"fires enforces nothing. Fired: {dict(counts)}"
    )


@pytest.mark.parametrize("rule_id", sorted(DECLARED))
def test_rule_is_silent_on_the_compliant_fixture(rule_id):
    """The half that stops the rule set being abandoned.

    `reference-tenant-scope-from-request` originally matched
    `request.state.auth.tenant_id` — the correct way to get a tenant. This
    assertion is what found it.
    """
    counts, _ = _run(COMPLIANT)
    assert counts.get(rule_id, 0) == 0, (
        f"{rule_id} fired on compliant code — a false positive. Rules that flag "
        f"the right answer get suppressed, and a suppressed rule reports success "
        f"forever after."
    )


# ----------------------------------------------------------- the meta-test


def test_a_config_path_that_matches_nothing_still_exits_zero(tmp_path):
    """Why assertion 1 exists, demonstrated rather than asserted.

    Point semgrep at an empty rules directory. It scans, finds nothing, and
    exits 0 — identical in every observable way to a clean scan with the real
    rule set. That is the failure mode, and no amount of reading the CI log
    distinguishes the two.
    """
    empty = tmp_path / "rules"
    empty.mkdir()
    (empty / "placeholder.yml").write_text("rules: []\n", encoding="utf-8")

    proc = subprocess.run(
        ["semgrep", "--config", str(empty), "--json", "--quiet",
         "--disable-version-check", str(NONCOMPLIANT)],
        capture_output=True, text=True,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0, "an empty rule set exits 0 — that is the point"
    assert payload.get("results") == [], "and reports no findings"

    real, _ = _run(NONCOMPLIANT)
    assert sum(real.values()) > 0, (
        "the real rule set finds the same code guilty, which is the only way to "
        "tell the two runs apart"
    )
