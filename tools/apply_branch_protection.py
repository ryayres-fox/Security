"""Apply branch protection as code, not as clicks in a settings page.

A protection rule configured through the web UI has the same problem as a
control matrix maintained in a spreadsheet: it is correct on the day it is set,
nothing records why, and nobody notices when it changes. This file is the rule
set, it is reviewable in a diff, and re-running it is idempotent.

    python tools/apply_branch_protection.py --repo owner/name
    python tools/apply_branch_protection.py --repo owner/name --check

`--check` reports drift without changing anything, which is the mode worth
running on a schedule: the interesting failure is not "protection was never
configured", it is "protection was configured and then quietly relaxed".

Requires the `gh` CLI, authenticated with admin on the repository.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# The check-run names CI produces. These must match the `name:` of each job
# exactly — a required check whose name does not exist is not enforced, it is
# simply never satisfied, and GitHub will happily report the branch as
# protected while the gate you meant to require never runs.
CHECKS = [
    "tests and lint (py3.11)",
    "tests and lint (py3.12)",
    "repo hygiene",
    "custom policies load and fire",
    "control mapping",
    "terraform",
    "IaC scan",
    "secrets scan",
    "normalizer end-to-end",
]

# Protection rises as changes move toward main. develop absorbs feature work,
# stage is the release candidate, main is what a reader is shown.
POLICY: dict[str, dict] = {
    "develop": {
        "required_status_checks": {"strict": True, "contexts": CHECKS},
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews": True,
        },
        "restrictions": None,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    },
    # NOTE on linear history, learned by using this model rather than by
    # designing it. Requiring it on a promotion branch forces every promotion PR
    # to be rebase-merged, which replays develop's commits onto stage under new
    # SHAs. The two branches then hold identical content with different history,
    # and the NEXT promotion cannot fast-forward or rebase — GitHub refuses the
    # merge outright.
    #
    # Linear history belongs to a squash-to-trunk model, where one branch is the
    # only destination. In a promotion model the merge commit IS the record of
    # the promotion, which is the thing worth keeping.
    "stage": {
        "required_status_checks": {"strict": True, "contexts": CHECKS},
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews": True,
        },
        "restrictions": None,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    },
    "main": {
        "required_status_checks": {"strict": True, "contexts": CHECKS},
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_last_push_approval": True,
        },
        "restrictions": None,
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    },
}


def gh_api(args: list[str], body: dict | None = None) -> tuple[int, str]:
    cmd = ["gh", "api", *args]
    if body is not None:
        cmd += ["--input", "-"]
    proc = subprocess.run(  # noqa: S603
        cmd,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout or proc.stderr)


def apply(repo: str, branch: str, rules: dict) -> tuple[bool, str]:
    code, out = gh_api(
        ["-X", "PUT", f"repos/{repo}/branches/{branch}/protection",
         "-H", "Accept: application/vnd.github+json"],
        rules,
    )
    return code == 0, out


def describe(repo: str, branch: str) -> dict | None:
    code, out = gh_api([f"repos/{repo}/branches/{branch}/protection"])
    if code != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def drift(actual: dict | None, wanted: dict) -> list[str]:
    if actual is None:
        return ["no protection configured at all"]
    problems = []

    got_checks = set(
        (actual.get("required_status_checks") or {}).get("contexts", []) or []
    )
    want_checks = set(wanted["required_status_checks"]["contexts"])
    if missing := want_checks - got_checks:
        problems.append(f"status checks not required: {sorted(missing)}")

    pairs = [
        ("allow_force_pushes", "enabled"),
        ("allow_deletions", "enabled"),
        ("required_linear_history", "disabled"),
        ("required_conversation_resolution", "disabled"),
    ]
    for key, bad_word in pairs:
        want = wanted.get(key)
        got = (actual.get(key) or {}).get("enabled")
        if want is not None and got is not None and want != got:
            problems.append(f"{key} is {bad_word}, expected {want}")

    want_reviews = wanted["required_pull_request_reviews"]["required_approving_review_count"]
    got_reviews = (actual.get("required_pull_request_reviews") or {}).get(
        "required_approving_review_count"
    )
    if got_reviews is None:
        problems.append("pull request reviews not required")
    elif got_reviews < want_reviews:
        problems.append(f"required reviews {got_reviews}, expected {want_reviews}")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    args = ap.parse_args(argv)

    failures = 0
    for branch, rules in POLICY.items():
        if args.check:
            problems = drift(describe(args.repo, branch), rules)
            if problems:
                failures += 1
                print(f"  {branch}: DRIFT")
                for p in problems:
                    print(f"      {p}")
            else:
                print(f"  {branch}: matches policy")
            continue

        ok, out = apply(args.repo, branch, rules)
        if ok:
            print(f"  {branch}: protection applied")
        else:
            failures += 1
            msg = out.strip().splitlines()[0] if out.strip() else "unknown error"
            print(f"  {branch}: FAILED — {msg}")
            if "Upgrade" in out or "upgrade" in out:
                print("      Branch protection on a PRIVATE repository requires a paid plan.")
                print("      Either make the repository public, or accept that these rules")
                print("      are documented but not enforced — and say which, out loud.")
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
