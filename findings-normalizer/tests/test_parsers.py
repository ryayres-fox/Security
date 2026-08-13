"""Parser tests.

Each parser gets three questions: does it read the real output shape, does it
map severity correctly, and does it produce an identity that survives a re-scan.
The fixtures in samples/ are the same files the README's quickstart uses, so a
drift between documentation and behaviour fails the build.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from findings_normalizer import parsers
from findings_normalizer.models import Severity
from findings_normalizer.parsers import asff, bandit, checkov, gitleaks, tfsec
from findings_normalizer.store import FindingStore

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _load(name: str):
    return json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("tool", parsers.SUPPORTED)
def test_every_supported_tool_has_a_runnable_sample(tool):
    """The registry and samples/ must not drift apart.

    A supported parser with no fixture is a parser nobody has ever run.
    """
    findings = parsers.get(tool).parse(_load(tool))
    assert findings, f"{tool} sample produced no findings"
    for f in findings:
        assert f.validate() == [], f"{tool} produced an invalid finding: {f.validate()}"
        assert f.finding_id and len(f.finding_id) == 16


@pytest.mark.parametrize("tool", parsers.SUPPORTED)
def test_parsing_is_deterministic(tool):
    """Same input, same identities — otherwise dedupe across runs is a fiction."""
    a = [f.finding_id for f in parsers.get(tool).parse(_load(tool))]
    b = [f.finding_id for f in parsers.get(tool).parse(_load(tool))]
    assert a == b


def test_unknown_tool_names_the_supported_set():
    with pytest.raises(KeyError, match="semgrep"):
        parsers.get("nessus")


def test_checkov_reads_the_multi_framework_list_shape():
    """Checkov emits a list when several frameworks run. Handling only the dict
    form yields zero findings and a green build — a silent fail-open."""
    out = checkov.parse(_load("checkov"))
    assert len(out) == 3, "terraform and kubernetes blocks must both be read"
    assert {f.rule_id for f in out} >= {"CKV_AWS_260", "CKV_K8S_20"}


def test_checkov_null_severity_defaults_to_medium_not_info():
    out = {f.rule_id: f for f in checkov.parse(_load("checkov"))}
    assert out["CKV_AWS_23"].severity is Severity.MEDIUM
    assert out["CKV_AWS_260"].severity is Severity.HIGH


def test_gitleaks_never_carries_the_secret_value():
    """The most important assertion in this file.

    Gitleaks output contains the matched credential. If the normalizer copies it
    into the store, the tool that finds the leak becomes a tool that spreads it.
    """
    raw = _load("gitleaks")
    secrets = {r["Secret"] for r in raw} | {r["Match"] for r in raw}
    blob = json.dumps([f.to_dict() for f in gitleaks.parse(raw)])
    for s in secrets:
        assert s not in blob, "secret material leaked into the normalized record"


def test_gitleaks_identity_is_commit_scoped_not_secret_scoped():
    out = gitleaks.parse(_load("gitleaks"))
    assert len({f.finding_id for f in out}) == 2
    assert all(f.severity is Severity.HIGH for f in out)
    assert all("IA-5" in f.control_ids for f in out)


def test_asff_skips_archived_and_resolved_findings():
    """Re-opening work someone already closed is how a normalizer loses trust."""
    out = asff.parse(_load("asff"))
    assert len(out) == 2
    assert all("CloudTrail.4" not in f.rule_id for f in out)


def test_asff_carries_control_ids_through_from_the_source():
    out = {f.rule_id: f for f in asff.parse(_load("asff"))}
    iam = out["nist-800-53/v/5.0.0/IAM.1"]
    assert iam.control_ids == ["AC-6", "AC-6(10)"]
    assert iam.severity is Severity.HIGH


def test_asff_uses_generator_id_so_the_same_control_dedupes():
    """`Id` is per-resource and unique per finding; using it would defeat dedupe."""
    out = asff.parse(_load("asff"))
    assert all(not f.rule_id.startswith("arn:") for f in out)


def test_tfsec_identity_uses_the_shared_avd_id_not_the_vendor_name():
    out = tfsec.parse(_load("tfsec"))
    assert {f.rule_id for f in out} == {"AVD-AWS-0107", "AVD-AWS-0057"}
    assert out[0].native_rule_id == "aws-vpc-no-public-ingress-sgr"
    assert out[0].severity is Severity.CRITICAL


def test_bandit_maps_cwe_and_keeps_confidence_out_of_severity():
    out = {f.rule_id: f for f in bandit.parse(_load("bandit"))}
    # B608 is MEDIUM severity with LOW confidence. Confidence must not demote it.
    assert out["B608"].severity is Severity.MEDIUM
    assert out["B608"].control_ids == ["CWE-89"]
    assert out["B501"].severity is Severity.HIGH


def test_tfsec_and_trivy_agree_on_the_same_misconfiguration():
    """Cross-tool dedupe, end to end, on real output shapes.

    Both tools report AVD-AWS-0107 on the same resource. That is one finding
    with two attributions, not two findings — and this is the assertion that
    proves the identity function actually does its job across vendors.
    """
    store = FindingStore()
    store.ingest(tfsec.parse(_load("tfsec")))
    store.ingest(parsers.get("trivy").parse(_load("trivy")))

    merged = [
        f
        for f in store.findings
        if f.location.resource_id == "aws_security_group_rule.admin_ingress"
    ]
    assert len(merged) == 1, "the same misconfiguration must fold into one record"
    assert merged[0].reported_by == {"tfsec", "trivy"}
    assert merged[0].severity is Severity.CRITICAL
