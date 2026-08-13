"""Prove the custom policy set loads AND fires.

Written because of a specific, real failure: a set of custom Checkov policies
that had never executed. There was no `__init__.py` in the policy directory, so
the external-checks loader registered zero checks — and the scan completed
normally, reported its usual counts, and CI went green. Nothing anywhere said
the policies were not running. The only way to notice was to ask whether they
*could* have failed, rather than to read their output.

That is why this file asserts two separate things. Either alone is a fail-open:

  1. **The loader registered the checks.** Catches the packaging failure — the
     policy set is present in the repository and absent from the scan.
  2. **A known-bad fixture actually produces a finding.** Catches the subtler
     case where checks register fine and never match anything, because a
     resource type is misspelled or a conf key changed shape in a Checkov
     upgrade. A check that registers and never fires is the same fail-open
     relocated one step later.

And one meta-assertion: that removing `__init__.py` really does break
registration, silently. Without it, assertion 1 might be passing for reasons
unrelated to what it claims to test.

These tests shell out to the Checkov CLI rather than importing its registry.
The CLI is the interface CI actually uses, and testing the interface you deploy
is worth more than testing a more convenient one underneath it.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
POLICY_DIR = HERE / "checkov"
NONCOMPLIANT = HERE / "fixtures" / "noncompliant"
COMPLIANT = HERE / "fixtures" / "compliant"

CHECK_ID = re.compile(r'id\s*=\s*["\'](CKV_CAC_\d+)["\']')


def _defined_check_ids() -> set[str]:
    """Every check ID declared in the policy directory, read from source.

    Deliberately derived from the files rather than hardcoded: adding a policy
    without it registering must fail this suite, and a hardcoded list would
    silently keep passing.
    """
    ids: set[str] = set()
    for path in POLICY_DIR.glob("check_*.py"):
        ids |= set(CHECK_ID.findall(path.read_text(encoding="utf-8")))
    return ids


DEFINED = _defined_check_ids()

pytestmark = pytest.mark.skipif(
    shutil.which("checkov") is None,
    reason="checkov CLI not installed — the CI policy job installs it explicitly",
)


def _run_checkov(target: Path, policy_dir: Path) -> dict[str, str]:
    """Return {check_id: 'PASSED'|'FAILED'} for custom checks only."""
    proc = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "checkov",
            "-d", str(target),
            "--external-checks-dir", str(policy_dir),
            "--compact",
            "-o", "json",
        ],
        capture_output=True,
        text=True,
    )
    if not proc.stdout.strip():
        raise AssertionError(f"checkov produced no output; stderr:\n{proc.stderr[:2000]}")

    payload = json.loads(proc.stdout)
    blocks = payload if isinstance(payload, list) else [payload]

    out: dict[str, str] = {}
    for block in blocks:
        results = block.get("results", {}) or {}
        for key, verdict in (("passed_checks", "PASSED"), ("failed_checks", "FAILED")):
            for check in results.get(key, []) or []:
                cid = check.get("check_id", "")
                if cid.startswith("CKV_CAC_"):
                    out[cid] = verdict
    return out


# --------------------------------------------------------------- sanity


def test_the_policy_directory_declares_checks_at_all():
    """Guards every other test in this file.

    If the ID regex stops matching — a refactor, a quoting change — DEFINED
    becomes empty and the parametrized tests below would silently collect zero
    cases and report success.
    """
    assert DEFINED, "no CKV_CAC_* check IDs found; the rest of this suite would be vacuous"
    assert len(DEFINED) == len(list(POLICY_DIR.glob("check_*.py"))), (
        "expected exactly one check ID per policy file"
    )


def test_init_py_exists():
    """The single file whose absence caused the original failure."""
    assert (POLICY_DIR / "__init__.py").exists(), (
        "no __init__.py: the external-checks loader will register zero checks "
        "and the scan will still report success"
    )


# ------------------------------------------------- assertion 1: registration


def test_every_defined_check_is_registered():
    registered = set(_run_checkov(NONCOMPLIANT, POLICY_DIR))
    missing = DEFINED - registered
    assert not missing, (
        f"defined but never registered: {sorted(missing)}. "
        "These policies exist in the repository and do not run."
    )


def test_registration_count_is_exact():
    """Catches a partially-wired policy set, which is the shape the original
    failure actually took — some files inside the configured directory, others
    outside every configured path."""
    registered = set(_run_checkov(NONCOMPLIANT, POLICY_DIR))
    assert len(registered) == len(DEFINED), (
        f"{len(DEFINED)} checks defined, {len(registered)} registered: "
        f"{sorted(DEFINED ^ registered)}"
    )


# ------------------------------------------------------ assertion 2: firing


@pytest.mark.parametrize("check_id", sorted(DEFINED))
def test_check_fails_on_the_noncompliant_fixture(check_id):
    """Registration is not enforcement. Each check must actually match."""
    results = _run_checkov(NONCOMPLIANT, POLICY_DIR)
    assert results.get(check_id) == "FAILED", (
        f"{check_id} did not report FAILED against the non-compliant fixture "
        f"(got {results.get(check_id, 'no result at all')}). "
        "A check that registers and never fires enforces nothing."
    )


@pytest.mark.parametrize("check_id", sorted(DEFINED))
def test_check_passes_on_the_compliant_fixture(check_id):
    """The other half. A policy set that fails everything gets suppressed within
    a week, and a suppressed check reports success forever after."""
    results = _run_checkov(COMPLIANT, POLICY_DIR)
    assert results.get(check_id) == "PASSED", (
        f"{check_id} did not pass the compliant fixture "
        f"(got {results.get(check_id, 'no result at all')}) — false positive"
    )


# ------------------------------------------------------------- the meta-test


def test_removing_init_py_breaks_registration_silently(tmp_path):
    """Proves the registration assertion is load-bearing, and reproduces the
    original failure exactly.

    Two things are asserted, and the second is the important one:
      - without __init__.py, zero custom checks register
      - checkov nonetheless completes and reports its normal built-in results

    That combination is what makes this class of defect invisible. There is no
    error, no warning, and no missing output — only a smaller number that nobody
    was counting.
    """
    broken = tmp_path / "checkov"
    shutil.copytree(POLICY_DIR, broken)
    (broken / "__init__.py").unlink()
    for cache in broken.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    results = _run_checkov(NONCOMPLIANT, broken)
    assert results == {}, (
        f"expected zero custom checks to register without __init__.py, got {results}. "
        "If this fails, Checkov's loader has changed and the registration test "
        "above may no longer be testing what it claims."
    )

    proc = subprocess.run(  # noqa: S603
        ["checkov", "-d", str(NONCOMPLIANT), "--external-checks-dir", str(broken),  # noqa: S607
         "--compact", "-o", "json"],
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    blocks = payload if isinstance(payload, list) else [payload]
    built_in = sum(
        len((b.get("results", {}) or {}).get(k, []) or [])
        for b in blocks
        for k in ("passed_checks", "failed_checks")
    )
    assert built_in > 0, (
        "the scan should still produce built-in results — that is precisely why "
        "the missing policies are invisible"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
