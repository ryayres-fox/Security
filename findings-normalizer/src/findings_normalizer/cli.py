"""Command-line interface.

    findings-normalize ingest --tool trivy --input samples/trivy.json
    findings-normalize report --format html --out report.html
    findings-normalize gate --fail-on critical,high

State persists to `.findings-store.json` between invocations, because ingest and
gate are separate CI steps in separate processes. An in-memory-only store would
work in the unit tests and fail in the pipeline, which is the wrong order to
discover a design problem in.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import parsers, report
from .models import Severity
from .store import FindingStore

DEFAULT_STATE = ".findings-store.json"
_EXIT_OK, _EXIT_GATE_FAILED, _EXIT_USAGE = 0, 1, 2


def _load_raw(path: str):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"input not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path} is not valid JSON: {e}") from None


def _severities(raw: str) -> list[Severity]:
    out = []
    for token in raw.split(","):
        token = token.strip().lower()
        if not token:
            continue
        try:
            out.append(Severity(token))
        except ValueError:
            raise SystemExit(
                f"unknown severity {token!r}; choose from "
                f"{', '.join(s.value for s in Severity)}"
            ) from None
    return out


def cmd_ingest(args) -> int:
    try:
        parser = parsers.get(args.tool)
    except KeyError as e:
        raise SystemExit(str(e)) from None

    findings = parser.parse(_load_raw(args.input))
    store = FindingStore.load(args.state)
    before = len(store.findings)
    scan_date = date.fromisoformat(args.scan_date) if args.scan_date else date.today()
    store.ingest(findings, scan_date=scan_date)
    store.save(args.state)

    new = len(store.findings) - before
    merged = len(findings) - new
    print(
        f"{args.tool}: parsed {len(findings)} · {new} new · "
        f"{merged} merged into existing · {len(store.findings)} tracked total"
    )
    return _EXIT_OK


def cmd_report(args) -> int:
    store = FindingStore.load(args.state)
    body = (
        report.to_html(store) if args.format == "html" else report.to_json(store)
    )
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
        print(f"wrote {args.out} ({len(store.findings)} findings)")
    else:
        print(body)
    return _EXIT_OK


def cmd_gate(args) -> int:
    store = FindingStore.load(args.state)
    fail_on = _severities(args.fail_on)
    passed, blocking = store.gate(fail_on)

    expired = store.expired_acceptances()
    if expired:
        print(f"note: {len(expired)} risk acceptance(s) past expiry, counted as active")

    if passed:
        print(f"gate passed · 0 active findings at {args.fail_on}")
        return _EXIT_OK

    print(f"gate FAILED · {len(blocking)} active finding(s) at {args.fail_on}\n")
    for f in sorted(blocking, key=lambda x: -x.severity.rank):
        where = f.location.file_path or f.location.resource_id or "—"
        print(f"  [{f.severity.value:<8}] {f.rule_id}  {where}")
        print(f"             {f.title}")
        print(f"             seen by: {', '.join(sorted(f.reported_by))}")
    return _EXIT_GATE_FAILED


def cmd_summary(args) -> int:
    store = FindingStore.load(args.state)
    print(json.dumps(report.summary(store), indent=2))
    return _EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="findings-normalize",
        description="Normalize multi-scanner security findings into one system of record.",
    )
    ap.add_argument(
        "--state", default=DEFAULT_STATE, help=f"store path (default: {DEFAULT_STATE})"
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_in = sub.add_parser("ingest", help="parse a scanner report into the store")
    p_in.add_argument("--tool", required=True, choices=parsers.SUPPORTED)
    p_in.add_argument("--input", required=True, help="path to the scanner's JSON output")
    p_in.add_argument(
        "--scan-date",
        help="ISO date to record this observation under (default: today). "
        "Backfilling history is what makes regression detection testable.",
    )
    p_in.set_defaults(func=cmd_ingest)

    p_rep = sub.add_parser("report", help="render the current state")
    p_rep.add_argument("--format", choices=["html", "json"], default="json")
    p_rep.add_argument("--out", help="write to a file instead of stdout")
    p_rep.set_defaults(func=cmd_report)

    p_gate = sub.add_parser("gate", help="exit non-zero if blocking findings are active")
    p_gate.add_argument(
        "--fail-on",
        default="critical,high",
        help="comma-separated severities that block (default: critical,high)",
    )
    p_gate.set_defaults(func=cmd_gate)

    p_sum = sub.add_parser("summary", help="print the summary block as JSON")
    p_sum.set_defaults(func=cmd_summary)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
