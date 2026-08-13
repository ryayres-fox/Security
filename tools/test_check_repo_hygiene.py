"""Tests for the hygiene gate.

The gate exists because of a specific incident: a job-search log naming target
companies was uploaded into this repository through the GitHub web UI, which
never consults .gitignore. So the first test is the regression test for that
exact filename, and the rest prove the gate fails when it should.

A checker that only ever passes is indistinguishable from no checker.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from check_repo_hygiene import (
    check_content,
    check_paths,
    main,
)

REPO = Path(__file__).resolve().parents[1]


def _git_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for name, body in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A", "-f"], cwd=tmp_path, check=True)
    return tmp_path


# ------------------------------------------------- the incident this prevents


def test_the_actual_file_that_caused_this_is_caught():
    """DAILY-SEARCH-LOG-2026-08-13.md reached the remote via the web UI.

    If this assertion ever fails, the gate has stopped covering the one case it
    was built for.
    """
    problems = check_paths(["DAILY-SEARCH-LOG-2026-08-13.md"])
    assert problems, "the file that caused this incident must be rejected"
    assert "job-search log" in problems[0]


@pytest.mark.parametrize(
    "path",
    [
        "DAILY-SEARCH-LOG-2026-08-13.md",
        "docs/daily_search_log.md",
        "JOB-SEARCH-NOTES.md",
        "APPLICATION-NOTES-2026.md",
        "SEARCH-PLAYBOOK.md",
        "letters/cover-letter-acme.md",
        "applications/reddit.md",
        "Ayres_Ryan_Resume_2026.pdf",
        "docs/resume.md",
        "RESUME-CLAIM-VERIFICATION-2026-08-13.md",
        "APPSEC-EVIDENCE-2026-08-01.md",
        "personal/notes.md",
        "private/thing.md",
        "notes-PERSONAL.md",
        ".env",
        "certs/server.pem",
        "secrets/keystore.jks",
        "home/id_rsa",
        "gcp-service-account-prod.json",
        "Security-repo-template.zip",
        "archive/backup.tar.gz",
        "Professional_Skills.xlsx",
        "notes.docx",
        "terraform.tfstate",
    ],
)
def test_forbidden_paths_are_rejected(path):
    assert check_paths([path]), f"{path} should have been rejected"


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "findings-normalizer/src/findings_normalizer/store.py",
        "reference-architecture/terraform/modules/iam-baseline/main.tf",
        "ai-security/prompt-injection/corpus.json",
        "docs/control-coverage.md",
        ".github/workflows/ci.yml",
        "findings-normalizer/samples/trivy.json",
    ],
)
def test_legitimate_repository_files_are_not_rejected(path):
    """Over-blocking gets a gate disabled, and a disabled gate still reports
    success from inside the workflow file."""
    assert check_paths([path]) == [], f"{path} is legitimate and must pass"


# ------------------------------------------------------------------- content


# Every credential-shaped fixture below is assembled from fragments so that no
# complete match exists in this file's own source.
#
# The alternative was to exempt this file from content scanning, which is the
# move this repository exists to argue against: it would mean a real credential
# pasted here later would sail past the gate. Assembling at runtime keeps the
# gate fully live on this file — these strings only become matchable in a
# tmp_path fixture that is never committed.
_PRIVATE_KEY = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIE...\n"
_AWS_KEY = "aws_access_key_id = " + "AKIA" + "IOSFODNN7EXAMPLE"
_GH_TOKEN = "token: " + "ghp_" + "a" * 36
_SLACK = "slack = " + "xoxb" + "-1234567890-abcdefghij"
_ACCOUNT = "arn:aws:iam::" + "1234567890" + "12" + ":role/thing"


def test_private_key_block_is_caught(tmp_path):
    (tmp_path / "leak.txt").write_text(_PRIVATE_KEY, encoding="utf-8")
    assert check_content(tmp_path, ["leak.txt"])


@pytest.mark.parametrize(
    "body,label",
    [
        (_AWS_KEY, "AWS access key ID"),
        (_GH_TOKEN, "GitHub personal access token"),
        (_SLACK, "Slack token"),
        (_ACCOUNT, "possible AWS account ID"),
    ],
)
def test_credential_markers_are_caught(tmp_path, body, label):
    (tmp_path / "f.txt").write_text(body, encoding="utf-8")
    found = check_content(tmp_path, ["f.txt"])
    assert found and label in found[0]


def test_documentation_placeholder_account_id_is_allowed(tmp_path):
    """000000000000 is the documentation placeholder and appears throughout the
    ASFF fixture. Flagging it would make the gate unusable on this repo."""
    (tmp_path / "f.json").write_text(
        'arn:aws:iam::000000000000:policy/example', encoding="utf-8"
    )
    assert check_content(tmp_path, ["f.json"]) == []


def test_content_exemptions_do_not_weaken_path_checks(tmp_path):
    """A file may be exempt from CONTENT scanning and still fail on PATH.

    Otherwise an exemption becomes a way to smuggle a forbidden file in.
    """
    assert check_paths(["personal/check_repo_hygiene.py"])


# ---------------------------------------------------------------- end to end


def test_gate_fails_on_a_repo_containing_a_search_log(tmp_path):
    root = _git_repo(tmp_path, {"DAILY-SEARCH-LOG-2026-08-13.md": "# log\n"})
    assert main(["--root", str(root)]) == 1


def test_gate_passes_on_a_clean_repo(tmp_path):
    root = _git_repo(tmp_path, {"README.md": "# hello\n", "src/a.py": "x = 1\n"})
    assert main(["--root", str(root)]) == 0


def test_gate_catches_a_force_added_file_that_gitignore_would_have_hidden(tmp_path):
    """The scenario .gitignore cannot cover.

    The file is listed in .gitignore AND tracked anyway — via `git add -f`, or a
    web upload, or because it was committed before the pattern existed. This is
    the entire reason the gate reads `git ls-files` rather than trusting
    .gitignore.
    """
    root = _git_repo(
        tmp_path,
        {
            ".gitignore": "*SEARCH-LOG*\n",
            "DAILY-SEARCH-LOG-2026-08-13.md": "# log\n",
        },
    )
    assert main(["--root", str(root)]) == 1


def test_this_repository_passes_its_own_gate(capsys):
    assert main(["--root", str(REPO)]) == 0
    assert "passed" in capsys.readouterr().out
