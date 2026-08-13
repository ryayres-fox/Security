"""Fail the build if personal, career, or credential material is tracked.

`.gitignore` did not prevent the incident that produced this script, and could
not have. A job-search log naming target companies reached this repository
through the GitHub web UI, which never consults `.gitignore` at all.

Three properties of `.gitignore` make it advisory rather than a control:

  1. It is client-side. Web uploads, API commits, and anything not going through
     a local `git add` bypass it entirely.
  2. It has no effect on a file that is already tracked. Adding a pattern after
     the fact changes nothing.
  3. `git add -f` overrides it, silently.

This checks what is actually *tracked*, in CI, on a machine that is not the
author's. That is where the enforcement has to live.

Two classes of check:

  PATH  — filenames that should never appear in a repository intended to become
          public. Career material, personal notes, credential files, archives.
  CONTENT — high-signal markers of real credential or account material inside
          tracked files.

Both are deliberately conservative about false positives, because a hygiene gate
that cries wolf gets disabled, and a disabled gate is worse than no gate: it
still appears in the workflow file and still reports success.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------- paths

FORBIDDEN_PATHS: list[tuple[str, str]] = [
    (r"(?i)search[-_]?log", "job-search log"),
    (r"(?i)job[-_]?search", "job-search material"),
    (r"(?i)application[-_]notes", "job application notes"),
    (r"(?i)search[-_]playbook", "job-search playbook"),
    (r"(?i)cover[-_]?letter", "cover letter"),
    (r"(?i)(^|/)applications?/", "job applications directory"),
    (r"(?i)(^|/)recruiters?/", "recruiter material"),
    (r"(?i)resume", "resume"),
    (r"(?i)curriculum[-_ ]?vitae", "CV"),
    (r"(?i)claim[-_]verification", "resume claim verification"),
    (r"(?i)appsec[-_]evidence", "internal evidence document"),
    (r"(?i)(^|/)personal/", "personal directory"),
    (r"(?i)(^|/)private/", "private directory"),
    (r"(?i)(^|/)scratchpad?/", "scratch directory"),
    (r"(?i)-personal\b", "file marked personal"),
    (r"(?i)\.env$", "environment file"),
    (r"(?i)\.(pem|p12|pfx|jks|keystore|kdbx|ppk)$", "key material"),
    (r"(?i)(^|/)id_(rsa|ed25519|ecdsa)", "SSH private key"),
    (r"(?i)(^|/)credentials(\.|$)", "credentials file"),
    (r"(?i)service[-_]account.*\.json$", "service account key"),
    (r"(?i)\.(zip|tar|tar\.gz|tgz|rar|7z)$", "archive"),
    (r"(?i)\.(docx?|xlsx?|pptx?)$", "office document"),
    (r"(?i)\.tfstate", "terraform state"),
]

# --------------------------------------------------------------------- content

FORBIDDEN_CONTENT: list[tuple[str, str]] = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key ID"),
    (r"\bASIA[0-9A-Z]{16}\b", "AWS temporary access key ID"),
    (r"\bghp_[A-Za-z0-9]{36}\b", "GitHub personal access token"),
    (r"\bgho_[A-Za-z0-9]{36}\b", "GitHub OAuth token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"\bsk-[A-Za-z0-9]{32,}\b", "API secret key"),
    # A 12-digit AWS account ID that is not the documentation placeholder.
    (r"(?<![\w.-])(?!0{12})\d{12}(?![\w.-])", "possible AWS account ID"),
]

# Paths exempt from CONTENT checks only. Never from PATH checks.
#
# Each entry needs a reason. An unexplained exemption is how a scanner becomes
# decorative — and this repository's own history contains a control that
# reported clean while enforcing nothing, so the bar here is explicit.
CONTENT_EXEMPT: list[tuple[str, str]] = [
    (
        r"^tools/check_repo_hygiene\.py$",
        "this file necessarily contains the patterns it searches for",
    ),
    (
        r"^\.terraform\.lock\.hcl$|/\.terraform\.lock\.hcl$",
        "provider lock hashes are 64-hex digests that can contain 12-digit runs",
    ),
]

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2"}


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _exempt_from_content(path: str) -> str | None:
    for pattern, reason in CONTENT_EXEMPT:
        if re.search(pattern, path):
            return reason
    return None


def check_paths(files: list[str]) -> list[str]:
    problems = []
    for f in files:
        for pattern, label in FORBIDDEN_PATHS:
            if re.search(pattern, f):
                problems.append(f"{f}: tracked {label} — must not be in this repository")
                break
    return problems


def check_content(root: Path, files: list[str]) -> list[str]:
    problems = []
    for f in files:
        if Path(f).suffix.lower() in BINARY_SUFFIXES or _exempt_from_content(f):
            continue
        p = root / f
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable; PATH checks still applied
        for pattern, label in FORBIDDEN_CONTENT:
            for m in re.finditer(pattern, text):
                line = text[: m.start()].count("\n") + 1
                problems.append(f"{f}:{line}: {label}")
                break
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument(
        "--staged",
        action="store_true",
        help="check only staged files (used by the pre-commit hook)",
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()

    if args.staged:
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [f for f in out.stdout.splitlines() if f.strip() and (root / f).exists()]
    else:
        files = tracked_files(root)

    problems = check_paths(files) + check_content(root, files)

    if problems:
        scope = "staged" if args.staged else "tracked"
        print(f"repo hygiene check FAILED · {len(problems)} problem(s) in {scope} files\n",
              file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nIf a match is a false positive, add it to CONTENT_EXEMPT in\n"
            "tools/check_repo_hygiene.py with a written reason. Do not disable the check.\n"
            "\nIf it is real and already committed, deleting it in a new commit is NOT\n"
            "enough — the content stays in history. Rewrite the history before pushing.",
            file=sys.stderr,
        )
        return 1

    scope = "staged" if args.staged else "tracked"
    print(f"repo hygiene check passed · {len(files)} {scope} files")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
