"""Fold every module's controls.yaml into a coverage report.

`docs/control-mapping.md` claims coverage is computable rather than maintained
by hand. This is the thing that makes that true. If it does not run in CI, the
claim degrades into a spreadsheet with extra steps.

What it checks, in `--check` mode:

  1. Every module directory containing `.tf` files has a `controls.yaml`.
     A module with no declared controls is a module whose claims live only in a
     README, which is where control matrices go to become wrong.
  2. Every control entry carries an `id`, a `statement` and an `evidence` field.
     "We implement AU-9" is an assertion. "Log file validation is enabled and
     here is the test" is a control.
  3. Every control ID is well-formed against the 800-53 family/number pattern.
     A typo'd ID silently produces a control nobody implements and nobody misses.
  4. Every declared exception names a check, a resource and a reason.

Deliberately NOT checked: whether a control is *satisfied*. This reports what is
implemented and enforced. Satisfaction is an assessor's judgment involving
policy, procedure and scope that do not live in this repository, and conflating
the two is how organizations get surprised at assessment.

Dependency-free: the subset of YAML used by controls.yaml is parsed here rather
than pulling in PyYAML, so this runs anywhere Python does.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CONTROL_ID = re.compile(r"^[A-Z]{2}-\d{1,2}(\(\d{1,2}\))?$")
REQUIRED_CONTROL_FIELDS = ("id", "statement", "evidence")
REQUIRED_EXCEPTION_FIELDS = ("check", "resource", "reason")

FAMILIES = {
    "AC": "Access Control",
    "AU": "Audit & Accountability",
    "AT": "Awareness & Training",
    "CM": "Configuration Management",
    "CP": "Contingency Planning",
    "IA": "Identification & Authentication",
    "IR": "Incident Response",
    "MA": "Maintenance",
    "MP": "Media Protection",
    "PE": "Physical & Environmental",
    "PL": "Planning",
    "PS": "Personnel Security",
    "RA": "Risk Assessment",
    "SA": "System & Services Acquisition",
    "SC": "System & Communications Protection",
    "SI": "System & Information Integrity",
    "SR": "Supply Chain Risk Management",
}


# --------------------------------------------------------------------- parsing


def parse_controls_yaml(text: str) -> dict:
    """Parse the flat `module:` / `implements:` / `exceptions:` shape.

    Not a general YAML parser and does not pretend to be. It handles exactly the
    structure controls.yaml uses and raises on anything else, which is the right
    trade: a partial parser that silently skips what it does not understand
    would under-report coverage, and under-reported coverage looks like success.
    """
    out: dict = {"module": None, "implements": [], "exceptions": []}
    section: str | None = None
    current: dict | None = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped[:-1]
            if key not in ("implements", "exceptions"):
                raise ValueError(f"line {lineno}: unexpected top-level key {key!r}")
            section, current = key, None
            continue

        if indent == 0 and ":" in stripped and not stripped.startswith("-"):
            key, _, value = stripped.partition(":")
            if key.strip() != "module":
                raise ValueError(f"line {lineno}: unexpected top-level key {key.strip()!r}")
            out["module"] = value.strip()
            section, current = None, None
            continue

        if stripped.startswith("- "):
            if section is None:
                raise ValueError(f"line {lineno}: list item outside a known section")
            key, _, value = stripped[2:].partition(":")
            current = {key.strip(): value.strip()}
            out[section].append(current)
            continue

        if current is not None and ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
            continue

        raise ValueError(f"line {lineno}: cannot parse {stripped!r}")

    return out


# ------------------------------------------------------------------- discovery


def find_modules(root: Path) -> list[Path]:
    """Every directory holding at least one .tf file is a module."""
    return sorted({p.parent for p in root.rglob("*.tf") if ".terraform" not in p.parts})


def collect(root: Path) -> tuple[list[dict], list[str]]:
    modules, problems = [], []

    for mod_dir in find_modules(root):
        manifest = mod_dir / "controls.yaml"
        rel = mod_dir.relative_to(root)

        if not manifest.exists():
            problems.append(f"{rel}: has .tf files but no controls.yaml")
            continue

        try:
            data = parse_controls_yaml(manifest.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{rel}/controls.yaml: {e}")
            continue

        name = data.get("module") or rel.name
        for entry in data["implements"]:
            missing = [f for f in REQUIRED_CONTROL_FIELDS if not entry.get(f)]
            if missing:
                problems.append(
                    f"{name}: control {entry.get('id', '?')} missing {', '.join(missing)}"
                )
            cid = entry.get("id", "")
            if cid and not CONTROL_ID.match(cid):
                problems.append(f"{name}: {cid!r} is not a well-formed 800-53 control ID")
            elif cid and cid.split("-")[0] not in FAMILIES:
                problems.append(f"{name}: {cid!r} names an unknown control family")

        for exc in data["exceptions"]:
            missing = [f for f in REQUIRED_EXCEPTION_FIELDS if not exc.get(f)]
            if missing:
                problems.append(
                    f"{name}: exception {exc.get('check', '?')} missing {', '.join(missing)}"
                )

        modules.append({"name": name, "path": str(rel), **data})

    return modules, problems


# --------------------------------------------------------------------- reports


def build_report(modules: list[dict]) -> dict:
    by_family: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for m in modules:
        for entry in m["implements"]:
            cid = entry.get("id", "")
            family = cid.split("-")[0] if "-" in cid else "?"
            by_family[family][cid].append(m["name"])

    return {
        "modules": len(modules),
        "controls_implemented": sum(len(m["implements"]) for m in modules),
        "distinct_controls": sum(len(c) for c in by_family.values()),
        "families_covered": sorted(by_family),
        "exceptions": sum(len(m["exceptions"]) for m in modules),
        "by_family": {
            fam: {cid: sorted(mods) for cid, mods in sorted(controls.items())}
            for fam, controls in sorted(by_family.items())
        },
    }


def to_markdown(modules: list[dict], report: dict) -> str:
    lines = [
        "# Control coverage",
        "",
        "Generated by `tools/control_coverage.py` from each module's `controls.yaml`.",
        "Do not edit by hand — the mapping moves with the code, which is the point.",
        "",
        (
            f"**{report['distinct_controls']} distinct controls** across "
            f"**{len(report['families_covered'])} families**, implemented by "
            f"**{report['modules']} modules**, with **{report['exceptions']} documented "
            "policy exceptions**."
        ),
        "",
        "> This reports what is *implemented and enforced*. It does not claim any control",
        "> is *satisfied* — that is an assessor's judgment involving policy, procedure and",
        "> scope that live outside this repository.",
        "",
        "## By family",
        "",
        "| Family | Control | Implemented by |",
        "| --- | --- | --- |",
    ]
    for fam, controls in report["by_family"].items():
        for cid, mods in controls.items():
            lines.append(f"| {fam} — {FAMILIES.get(fam, '?')} | `{cid}` | {', '.join(mods)} |")

    lines += ["", "## By module", ""]
    for m in sorted(modules, key=lambda x: x["name"]):
        ids = ", ".join(f"`{e['id']}`" for e in m["implements"])
        lines.append(f"### {m['name']}")
        lines.append("")
        lines.append(f"`{m['path']}` — {ids or '_none declared_'}")
        lines.append("")
        for entry in m["implements"]:
            lines.append(f"- **{entry['id']}** — {entry['statement']}")
            lines.append(f"  - *Evidence:* {entry['evidence']}")
        if m["exceptions"]:
            lines.append("")
            lines.append("**Documented exceptions**")
            lines.append("")
            for exc in m["exceptions"]:
                lines.append(f"- `{exc['check']}` on `{exc['resource']}` — {exc['reason']}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default="reference-architecture", type=Path)
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--out", help="write to a file instead of stdout")
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if any module lacks a controls.yaml or any entry is malformed",
    )
    args = ap.parse_args(argv)

    if not args.root.exists():
        print(f"root not found: {args.root}", file=sys.stderr)
        return 2

    modules, problems = collect(args.root)
    report = build_report(modules)

    if args.check:
        if problems:
            print(f"control-mapping check FAILED · {len(problems)} problem(s)\n", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1
        print(
            f"control-mapping check passed · {report['modules']} modules · "
            f"{report['distinct_controls']} distinct controls · "
            f"{report['exceptions']} documented exceptions"
        )
        return 0

    body = (
        json.dumps(report, indent=2)
        if args.format == "json"
        else to_markdown(modules, report)
    )
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(body)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
