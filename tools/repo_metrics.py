"""Compute the repository's own metrics, and name the unit for every one.

The repository's stated principle is that a number nobody can reproduce is a
number nobody should quote. So these are derived from the tree at build time
rather than typed into a README, the generated file is committed, and CI diffs
it — a stale metric fails the build like a stale diagram does.

Each row states its unit explicitly. "141 tests" is ambiguous between test
functions and collected cases (parametrization makes those very different
numbers), and the difference is exactly the kind of thing that turns a good
claim into a bad interview moment.

    python tools/repo_metrics.py            # write docs/metrics.md
    python tools/repo_metrics.py --check    # fail if committed output is stale
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

OUT = Path("docs/metrics.md")
SKIP_DIRS = {".git", ".terraform", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}


def tracked(root: Path) -> list[Path]:
    """Only tracked files count. Untracked scratch would inflate every number."""
    proc = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "ls-files"],  # noqa: S607
        capture_output=True, text=True, check=True,
    )
    return [root / line for line in proc.stdout.splitlines() if line.strip()]


def _py_stats(files: list[Path]) -> tuple[int, int, int, int]:
    """(modules, test functions, code lines, comment+docstring lines)"""
    modules = tests = code = docs = 0
    for f in files:
        if f.suffix != ".py":
            continue
        modules += 1
        src = f.read_text(encoding="utf-8")
        for line in src.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                docs += 1
            else:
                code += 1
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                tests += 1
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                doc = ast.get_docstring(node)
                if doc:
                    docs += len(doc.splitlines())
    return modules, tests, code, docs


def _tf_stats(files: list[Path]) -> tuple[int, int, int]:
    """(module directories, declared resource blocks, .tf lines)

    Scoped to reference-architecture/. The policy fixtures under policies/ are
    also .tf, and counting them as modules would inflate the module count with
    files that exist to be scanned rather than deployed — the exact kind of
    unit error this file exists to avoid making.
    """
    mods, resources, lines = set(), 0, 0
    for f in files:
        if f.suffix != ".tf" or "reference-architecture" not in f.parts:
            continue
        mods.add(f.parent)
        text = f.read_text(encoding="utf-8")
        lines += len(text.splitlines())
        resources += len(re.findall(r'^resource\s+"', text, re.MULTILINE))
    return len(mods), resources, lines


def _controls(files: list[Path]) -> tuple[int, int, int]:
    """(distinct control IDs, families, declared exceptions)"""
    ids, exceptions = set(), 0
    for f in files:
        if f.name != "controls.yaml":
            continue
        text = f.read_text(encoding="utf-8")
        ids |= set(re.findall(r"^\s*-\s*id:\s*(\S+)", text, re.MULTILINE))
        exceptions += len(re.findall(r"^\s*-\s*check:\s*\S+", text, re.MULTILINE))
    return len(ids), len({i.split("-")[0] for i in ids}), exceptions


def collect(root: Path) -> dict:
    files = [f for f in tracked(root) if f.exists()]
    modules, tests, code, docs = _py_stats(files)
    tf_mods, tf_resources, tf_lines = _tf_stats(files)
    ctl_ids, ctl_fams, ctl_exc = _controls(files)

    parsers = sorted(
        p.stem for p in (root / "findings-normalizer/src/findings_normalizer/parsers").glob("*.py")
        if p.stem != "__init__"
    )
    fixtures = sorted(p.stem for p in (root / "findings-normalizer/samples").glob("*.json"))
    policies = sorted(p.stem for p in (root / "policies/checkov").glob("check_*.py"))
    diagrams = sorted(p.stem for p in (root / "docs/diagrams").glob("*.svg"))

    corpus_path = root / "ai-security/prompt-injection/corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]

    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    ci_jobs = len(re.findall(r"^  [a-z][a-z0-9-]*:$", ci, re.MULTILINE))
    pinned = len(re.findall(r"uses: \S+@[0-9a-f]{40}", ci))
    unpinned = len(re.findall(r"uses: \S+@(?![0-9a-f]{40})", ci))

    return {
        "tracked_files": len(files),
        "py_modules": modules,
        "py_tests": tests,
        "py_code_lines": code,
        "py_doc_lines": docs,
        "tf_modules": tf_mods,
        "tf_resources": tf_resources,
        "tf_lines": tf_lines,
        "controls": ctl_ids,
        "families": ctl_fams,
        "exceptions": ctl_exc,
        "parsers": parsers,
        "fixtures": fixtures,
        "policies": policies,
        "diagrams": diagrams,
        "corpus_total": len(corpus),
        "corpus_deny": sum(1 for c in corpus if c["expect"] == "deny"),
        "corpus_allow": sum(1 for c in corpus if c["expect"] == "allow"),
        "ci_jobs": ci_jobs,
        "actions_pinned": pinned,
        "actions_unpinned": unpinned,
    }


def render(m: dict) -> str:
    rows = [
        ("Tracked files", m["tracked_files"],
         "files in `git ls-files`; untracked scratch excluded"),
        ("Python modules", m["py_modules"], "tracked `.py` files"),
        ("Test functions", m["py_tests"],
         "functions named `test_*`, by AST. **Not** collected cases — parametrization "
         "expands these to more"),
        ("Python code lines", m["py_code_lines"], "non-blank, non-comment"),
        ("Comment + docstring lines", m["py_doc_lines"],
         "the reasoning, which is most of the point here"),
        ("Terraform modules", m["tf_modules"],
         "directories under `reference-architecture/` with at least one `.tf`; "
         "policy fixtures excluded"),
        ("Resource declarations", m["tf_resources"],
         "`resource \"…\"` blocks. Declarations, **not** live instances"),
        ("Terraform lines", m["tf_lines"], "raw `.tf` line count"),
        ("Distinct controls", m["controls"],
         f"unique 800-53 IDs across `controls.yaml`, spanning {m['families']} families"),
        ("Documented exceptions", m["exceptions"],
         "scanner suppressions, each inline with a written reason"),
        ("Custom policies", len(m["policies"]), "Checkov checks asserted to register *and* fire"),
        ("Scanner parsers", len(m["parsers"]), ", ".join(m["parsers"])),
        ("Parser fixtures", len(m["fixtures"]), "one per parser; a registry test enforces parity"),
        ("Injection corpus", m["corpus_total"],
         f"{m['corpus_deny']} must deny, {m['corpus_allow']} must allow — the allow cases are "
         "what stop a gate hardcoded to DENY from passing"),
        ("CI jobs", m["ci_jobs"], "all blocking; `soft_fail` is never used"),
        ("Actions pinned by SHA", m["actions_pinned"],
         f"{m['actions_unpinned']} pinned by tag — a tag is a pin someone else can rewrite"),
        ("Generated diagrams", len(m["diagrams"]), ", ".join(m["diagrams"])),
    ]
    lines = [
        "# Metrics",
        "",
        "Generated by [`tools/repo_metrics.py`](../tools/repo_metrics.py) from the tracked tree.",
        "Do not edit by hand — CI diffs this against a fresh run, so a stale number fails",
        "the build.",
        "",
        "**Every row names its unit.** A number that cannot survive *\"how did you count that?\"*",
        "should not be quoted, and the fastest way to fail that question is to have never decided",
        "what was being counted.",
        "",
        "| Metric | Count | Unit / note |",
        "| --- | ---: | --- |",
    ]
    for label, value, note in rows:
        lines.append(f"| {label} | **{value}** | {note} |")
    lines += [
        "",
        "## What is deliberately not here",
        "",
        "No lines-of-code total presented as an achievement, no scanner count presented as",
        "coverage, and no percentage without a denominator. Volume metrics describe how busy a",
        "repository was, not whether anything in it holds.",
        "",
        "The numbers worth defending are in the right-hand column: that every declared control",
        "names its evidence, that every suppression carries a reason, and that the custom policy",
        "set is asserted to run rather than assumed to.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--out", default=OUT, type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    body = render(collect(args.root.resolve()))
    if args.check:
        if not args.out.exists() or args.out.read_text(encoding="utf-8") != body:
            print(f"metrics check FAILED · {args.out} is stale", file=sys.stderr)
            print("Regenerate:  python tools/repo_metrics.py", file=sys.stderr)
            return 1
        print("metrics check passed · docs/metrics.md matches the tree")
        return 0

    args.out.write_text(body, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
