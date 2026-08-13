"""Reporting.

The HTML report is a single self-contained file with no external assets. A
report that needs a CDN is a report that renders blank inside the networks where
this kind of tooling actually runs.
"""
from __future__ import annotations

import html
import json
from datetime import date

from .models import Severity
from .store import FindingStore

_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]

_COLORS = {
    "critical": "#b3261e",
    "high": "#d1642a",
    "medium": "#a6822a",
    "low": "#3d6b8e",
    "info": "#5f6b7a",
}


def summary(store: FindingStore, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    counts = store.counts_by_severity(as_of)
    return {
        "generated": as_of.isoformat(),
        "total_findings": len(store.findings),
        "active": len(store.active(as_of)),
        "triage_rate": round(store.triage_rate(as_of), 4),
        "by_severity": {s.value: counts.get(s.value, 0) for s in _ORDER},
        "by_tool_class": store.counts_by_tool_class(as_of),
        "scan_dates": [d.isoformat() for d in store.scan_dates()],
        "regressions": len(store.regressions()),
        "expired_acceptances": len(store.expired_acceptances(as_of)),
        "control_coverage": store.control_coverage(),
    }


def to_json(store: FindingStore, as_of: date | None = None) -> str:
    as_of = as_of or date.today()
    payload = {
        "summary": summary(store, as_of),
        "findings": [
            {
                **f.to_dict(),
                "first_seen": (
                    d.isoformat() if (d := store.first_seen(f.finding_id)) else None
                ),
                "last_seen": (
                    d.isoformat() if (d := store.last_seen(f.finding_id)) else None
                ),
                "age_days": store.age_days(f.finding_id, as_of),
                "regression": store.is_regression(f.finding_id),
            }
            for f in sorted(
                store.findings, key=lambda x: (-x.severity.rank, x.tool_class, x.rule_id)
            )
        ],
    }
    return json.dumps(payload, indent=2)


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else "—"


def to_html(store: FindingStore, as_of: date | None = None) -> str:
    as_of = as_of or date.today()
    s = summary(store, as_of)

    tiles = "".join(
        f'<div class="tile">'
        f'<span class="n" style="color:{_COLORS[sev]}">{s["by_severity"][sev]}</span>'
        f'<span class="l">{sev}</span></div>'
        for sev in [x.value for x in _ORDER]
    )

    rows = []
    for f in sorted(
        store.findings, key=lambda x: (-x.severity.rank, x.tool_class, x.rule_id)
    ):
        first = store.first_seen(f.finding_id)
        age = store.age_days(f.finding_id, as_of)
        flags = []
        if store.is_regression(f.finding_id):
            flags.append('<span class="flag reg">regression</span>')
        if f.is_expired(as_of):
            flags.append('<span class="flag exp">acceptance expired</span>')
        rows.append(
            "<tr>"
            f'<td><span class="sev" style="background:{_COLORS[f.severity.value]}">'
            f"{f.severity.value}</span></td>"
            f"<td><code>{_esc(f.rule_id)}</code>{''.join(flags)}</td>"
            f"<td>{_esc(f.title)}</td>"
            f"<td><code>{_esc(f.location.file_path or f.location.resource_id)}</code></td>"
            f"<td>{_esc(f.tool_class)}</td>"
            f'<td>{_esc(", ".join(sorted(f.reported_by)))}</td>'
            f'<td>{_esc(", ".join(f.control_ids) or None)}</td>'
            f"<td>{_esc(f.disposition.value)}</td>"
            f"<td>{_esc(f.owner)}</td>"
            f'<td class="num">{_esc(age)}</td>'
            f"<td>{_esc(first.isoformat() if first else None)}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Findings report — {s["generated"]}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#fff; --fg:#16191d; --mut:#5f6b7a;
           --line:#e3e6ea; --card:#f7f8fa; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#14171a; --fg:#e8eaed; --mut:#9aa4b0; --line:#2a2f36; --card:#1c2025; }}
  }}
  body {{ margin:0; padding:2rem 1.25rem; background:var(--bg); color:var(--fg);
         font:15px/1.5 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif; }}
  main {{ max-width:1200px; margin:0 auto; }}
  h1 {{ font-size:1.35rem; margin:0 0 .25rem; }}
  .sub {{ color:var(--mut); margin:0 0 1.5rem; font-size:.9rem; }}
  .tiles {{ display:flex; flex-wrap:wrap; gap:.75rem; margin-bottom:1rem; }}
  .tile {{ background:var(--card); border:1px solid var(--line); border-radius:8px;
           padding:.75rem 1.1rem; min-width:88px; }}
  .tile .n {{ display:block; font-size:1.6rem; font-weight:650;
               font-variant-numeric:tabular-nums; }}
  .tile .l {{ display:block; color:var(--mut); font-size:.78rem; text-transform:uppercase;
              letter-spacing:.04em; }}
  .meta {{ color:var(--mut); font-size:.85rem; margin-bottom:1.5rem; }}
  .meta b {{ color:var(--fg); font-variant-numeric:tabular-nums; }}
  .wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; }}
  table {{ border-collapse:collapse; width:100%; font-size:.85rem; }}
  th,td {{ text-align:left; padding:.5rem .65rem; border-bottom:1px solid var(--line);
           vertical-align:top; }}
  th {{ background:var(--card); font-weight:600; white-space:nowrap; position:sticky; top:0; }}
  tr:last-child td {{ border-bottom:none; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  code {{ font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-all; }}
  .sev {{ color:#fff; padding:.1rem .45rem; border-radius:4px; font-size:.72rem;
          text-transform:uppercase; letter-spacing:.03em; white-space:nowrap; }}
  .flag {{ display:inline-block; margin-left:.4rem; padding:.05rem .35rem; border-radius:4px;
           font-size:.68rem; border:1px solid currentColor; white-space:nowrap; }}
  .flag.reg {{ color:#b3261e; }} .flag.exp {{ color:#a6822a; }}
</style></head><body><main>
<h1>Findings report</h1>
<p class="sub">Generated {s["generated"]} · {len(s["scan_dates"])} scan date(s) ingested</p>
<div class="tiles">{tiles}</div>
<p class="meta">
  <b>{s["active"]}</b> active of <b>{s["total_findings"]}</b> tracked ·
  triage rate <b>{s["triage_rate"]:.1%}</b> ·
  <b>{s["regressions"]}</b> regression(s) ·
  <b>{s["expired_acceptances"]}</b> expired acceptance(s)
</p>
<div class="wrap"><table>
<thead><tr>
  <th>Severity</th><th>Rule</th><th>Title</th><th>Location</th><th>Class</th>
  <th>Reported by</th><th>Controls</th><th>Disposition</th><th>Owner</th>
  <th>Age (d)</th><th>First seen</th>
</tr></thead>
<tbody>{"".join(rows) or '<tr><td colspan="11">No findings.</td></tr>'}</tbody>
</table></div>
</main></body></html>"""
