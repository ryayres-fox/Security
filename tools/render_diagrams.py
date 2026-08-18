"""Render the repository's architecture diagrams as SVG.

Why generated rather than drawn:

A diagram exported from a drawing tool is a screenshot of what was true the day
someone opened the tool. It has no relationship to the code afterwards, and the
first refactor makes it quietly wrong — which is the same defect class this
repository keeps writing about, in a place nobody thinks to check.

These are defined as data, rendered deterministically, committed, and diffed in
CI. A stale diagram fails the build.

The stencil below is an original icon set drawn in the AWS architecture-diagram
visual language: category-coloured rounded tiles with white glyphs, the same
convention a Visio stencil uses, so an EC2 node, a Lambda function, an EKS
cluster and a switch are each recognisable at a glance rather than being three
identical rectangles with different words in them. No vendor icon assets are
copied; every glyph here is drawn from primitives.

    python tools/render_diagrams.py            # write docs/diagrams/*.svg
    python tools/render_diagrams.py --check     # fail if committed output is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT_DIR = Path("docs/diagrams")

# AWS architecture-icon category colours.
C_COMPUTE = "#ED7100"
C_CONTAINER = "#ED7100"
C_STORAGE = "#7AA116"
C_DATABASE = "#2E73B8"
C_NETWORK = "#8C4FFF"
C_SECURITY = "#DD344C"
C_MGMT = "#E7157B"
C_DEVTOOLS = "#4D27AA"
C_ONPREM = "#5A6B7B"

INK = "#232F3E"       # AWS "squid ink" — headings and text
MUTED = "#5A6B7B"
LINE = "#8393A3"
PAPER = "#FFFFFF"
PANEL = "#F6F8FA"
OK = "#1D8102"
BAD = "#D13212"

# Smallest legible size in a diagram a browser will scale down. Anything under
# this reads as texture rather than text once GitHub fits it to a column, so the
# floor is applied centrally rather than trusted to each call site — and there
# is a test asserting no rendered glyph falls below it.
MIN_FONT = 10.5

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


# --------------------------------------------------------------------- glyphs
# Each glyph is drawn inside a 48x48 box at origin (0,0), in white.

GLYPHS: dict[str, tuple[str, str]] = {
    "ec2": (C_COMPUTE, """
        <rect x="12" y="11" width="24" height="26" rx="2" fill="none" stroke="#fff" stroke-width="2.2"/>
        <path d="M17 17h14M17 22h14M17 27h9" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
        <path d="M9 16v16M39 16v16" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    """),
    "lambda": (C_COMPUTE, """
        <path d="M14 36 24 12l10 24" fill="none" stroke="#fff" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M19 25h7" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>
    """),
    "eks": (C_CONTAINER, """
        <path d="M24 9 38 16.5v15L24 39 10 31.5v-15z" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linejoin="round"/>
        <circle cx="24" cy="24" r="4" fill="#fff"/>
        <path d="M24 20V14M27.5 26.5 33 30M20.5 26.5 15 30" stroke="#fff" stroke-width="2"
              stroke-linecap="round"/>
    """),
    "s3": (C_STORAGE, """
        <path d="M13 13h22l-3 22H16z" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linejoin="round"/>
        <path d="M13.8 19h20.4" stroke="#fff" stroke-width="2"/>
        <circle cx="28.5" cy="28" r="2.2" fill="#fff"/>
    """),
    "s3lock": (C_STORAGE, """
        <path d="M13 13h22l-3 22H16z" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linejoin="round"/>
        <rect x="19" y="24" width="11" height="8" rx="1.4" fill="#fff"/>
        <path d="M21.5 24v-2.5a3 3 0 0 1 6 0V24" fill="none" stroke="#fff" stroke-width="2"/>
    """),
    "kms": (C_SECURITY, """
        <circle cx="19" cy="20" r="6.5" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M23.5 24.5 35 36" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>
        <path d="M31 32l-3.5 3.5M34 29l-3 3" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    """),
    "iam": (C_SECURITY, """
        <path d="M24 10l12 4.5v9c0 8-5.2 12.6-12 14.5-6.8-1.9-12-6.5-12-14.5v-9z"
              fill="none" stroke="#fff" stroke-width="2.4" stroke-linejoin="round"/>
        <circle cx="24" cy="21" r="3.2" fill="#fff"/>
        <path d="M18.5 31c1.2-3 3.1-4.4 5.5-4.4s4.3 1.4 5.5 4.4" fill="none" stroke="#fff"
              stroke-width="2.2" stroke-linecap="round"/>
    """),
    "cloudtrail": (C_MGMT, """
        <rect x="11" y="11" width="26" height="26" rx="3" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M16 18h16M16 24h16M16 30h10" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    """),
    "cloudwatch": (C_MGMT, """
        <circle cx="24" cy="24" r="13" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M14 27l5-6 4 4 5-8 6 10" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linecap="round" stroke-linejoin="round"/>
    """),
    "sns": (C_MGMT, """
        <circle cx="17" cy="24" r="4.5" fill="#fff"/>
        <path d="M25 16c3.5 2.2 3.5 13.8 0 16M30 12c5.5 3.4 5.5 20.6 0 24"
              fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>
    """),
    "alb": (C_NETWORK, """
        <circle cx="24" cy="14" r="4" fill="#fff"/>
        <path d="M24 18v6M24 24H12v6M24 24h12v6M24 24v6" fill="none" stroke="#fff"
              stroke-width="2.2" stroke-linecap="round"/>
        <rect x="8" y="30" width="8" height="7" rx="1.5" fill="#fff"/>
        <rect x="20" y="30" width="8" height="7" rx="1.5" fill="#fff"/>
        <rect x="32" y="30" width="8" height="7" rx="1.5" fill="#fff"/>
    """),
    "natgw": (C_NETWORK, """
        <rect x="10" y="14" width="28" height="20" rx="3" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M15 21h13l-3.5-3.5M33 27H20l3.5 3.5" fill="none" stroke="#fff" stroke-width="2.2"
              stroke-linecap="round" stroke-linejoin="round"/>
    """),
    "igw": (C_NETWORK, """
        <rect x="9" y="17" width="30" height="14" rx="3" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M14 24h20" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 11v6M24 31v6" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    """),
    "vgw": (C_NETWORK, """
        <rect x="9" y="18" width="30" height="13" rx="3" fill="none" stroke="#fff" stroke-width="2.4"/>
        <rect x="19" y="9" width="10" height="8" rx="1.6" fill="#fff"/>
        <path d="M21.4 9V7a2.6 2.6 0 0 1 5.2 0v2" fill="none" stroke="#fff" stroke-width="1.9"/>
        <path d="M15 24.5h18" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    """),
    "waf": (C_SECURITY, """
        <path d="M10 14h28v20H10z" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M10 20.7h28M10 27.3h28M19 14v6.7M29 14v6.7M15 20.7v6.6M24 20.7v6.6
                 M33 20.7v6.6M19 27.3V34M29 27.3V34" stroke="#fff" stroke-width="1.8"/>
    """),
    "switch": (C_ONPREM, """
        <rect x="7" y="18" width="34" height="13" rx="2" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M12 31v5M18 31v5M24 31v5M30 31v5M36 31v5" stroke="#fff" stroke-width="2"
              stroke-linecap="round"/>
        <path d="M13 24.5h9l-2.5-2.5M35 24.5h-9l2.5 2.5" fill="none" stroke="#fff"
              stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
    """),
    "router": (C_ONPREM, """
        <circle cx="24" cy="24" r="13" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M24 15v13M24 15l-3 3.5M24 15l3 3.5" fill="none" stroke="#fff" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M17 30h14M17 30l3-3M31 30l-3 3" fill="none" stroke="#fff" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"/>
    """),
    "firewall": (C_SECURITY, """
        <path d="M11 13h26v22H11z" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M11 20.3h26M11 27.6h26M20 13v7.3M29 13v7.3M16 20.3v7.3M25 20.3v7.3
                 M33 20.3v7.3M20 27.6V35M29 27.6V35" stroke="#fff" stroke-width="1.7"/>
    """),
    "github": (C_DEVTOOLS, """
        <circle cx="24" cy="24" r="6" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M24 8v6M24 34v6M8 24h6M34 24h6M13 13l4.2 4.2M30.8 30.8 35 35M35 13l-4.2 4.2
                 M17.2 30.8 13 35" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    """),
    "scanner": (C_DEVTOOLS, """
        <circle cx="21" cy="21" r="8.5" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M27.5 27.5 37 37" stroke="#fff" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M17 21h8M21 17v8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    """),
    "dynamodb": (C_DATABASE, """
        <ellipse cx="24" cy="15" rx="12" ry="4.5" fill="none" stroke="#fff" stroke-width="2.4"/>
        <path d="M12 15v18c0 2.5 5.4 4.5 12 4.5s12-2 12-4.5V15" fill="none" stroke="#fff"
              stroke-width="2.4"/>
        <path d="M12 24c0 2.5 5.4 4.5 12 4.5s12-2 12-4.5" fill="none" stroke="#fff" stroke-width="2"/>
    """),
    "vector": (C_DATABASE, """
        <circle cx="15" cy="16" r="3" fill="#fff"/><circle cx="30" cy="13" r="3" fill="#fff"/>
        <circle cx="34" cy="28" r="3" fill="#fff"/><circle cx="18" cy="31" r="3" fill="#fff"/>
        <circle cx="24" cy="22" r="3.4" fill="none" stroke="#fff" stroke-width="2"/>
        <path d="M17.4 17.2 21.4 20M27.2 14.6 25.6 19M31.6 26.4 27 23.4M20.4 29.4 22.6 25.2"
              stroke="#fff" stroke-width="1.7"/>
    """),
    "model": (C_DEVTOOLS, """
        <rect x="11" y="13" width="26" height="22" rx="4" fill="none" stroke="#fff" stroke-width="2.4"/>
        <circle cx="18.5" cy="22" r="2.4" fill="#fff"/><circle cx="29.5" cy="22" r="2.4" fill="#fff"/>
        <path d="M18 29h12" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M24 13V8" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>
    """),
    "gate": (C_SECURITY, """
        <rect x="8" y="11" width="6" height="28" rx="2" fill="#fff"/>
        <rect x="17" y="17" width="24" height="9" rx="2" fill="none" stroke="#fff" stroke-width="2.2"/>
        <path d="M22 17l-4 9M28 17l-4 9M34 17l-4 9M40 17l-4 9" stroke="#fff" stroke-width="1.7"/>
        <path d="M17 34h24" stroke="#fff" stroke-width="2.2" stroke-linecap="round"
              stroke-dasharray="3 3"/>
    """),
    "report": (C_MGMT, """
        <path d="M14 9h13l8 8v22H14z" fill="none" stroke="#fff" stroke-width="2.4"
              stroke-linejoin="round"/>
        <path d="M27 9v8h8" fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/>
        <path d="M19 24h11M19 29h11M19 34h7" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
    """),
}


# ------------------------------------------------------------------ primitives


def icon(name: str, x: float, y: float, label: str, sub: str = "", size: float = 48) -> str:
    """A stencil tile plus its caption, positioned by the tile's top-left."""
    color, glyph = GLYPHS[name]
    s = size / 48
    out = [
        f'<g transform="translate({x},{y})">',
        f'  <rect width="{size}" height="{size}" rx="{7 * s:.1f}" fill="{color}"/>',
        f'  <g transform="scale({s:.4f})">{glyph}</g>',
        f'  <text x="{size / 2}" y="{size + 15}" text-anchor="middle" font-family="{FONT}"'
        f' font-size="12.5" font-weight="600" fill="{INK}">{escape(label)}</text>',
    ]
    if sub:
        out.append(
            f'  <text x="{size / 2}" y="{size + 26}" text-anchor="middle" font-family="{FONT}"'
            f' font-size="11" fill="{MUTED}">{escape(sub)}</text>'
        )
    out.append("</g>")
    return "\n".join(out)


def boundary(x, y, w, h, label, color, dashed=True, fill="none", label_color=None) -> str:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    lc = label_color or color
    return (
        f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}"'
        f' stroke="{color}" stroke-width="1.8"{dash}/>'
        f'<text x="{x + 12}" y="{y + 19}" font-family="{FONT}" font-size="11.5"'
        f' font-weight="700" letter-spacing="0.4" fill="{lc}">{escape(label)}</text></g>'
    )


def arrow(x1, y1, x2, y2, label="", color=LINE, dashed=False, curve=0) -> str:
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    if curve:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + curve
        d = f"M{x1},{y1} Q{mx},{my} {x2},{y2}"
    else:
        d = f"M{x1},{y1} L{x2},{y2}"
    out = [
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{dash}'
        f' marker-end="url(#arrow)"/>'
    ]
    if label:
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 + (curve * 0.6) - 6
        out.append(
            f'<rect x="{lx - len(label) * 3.1 - 5}" y="{ly - 10}" width="{len(label) * 6.2 + 10}"'
            f' height="15" rx="3" fill="{PAPER}" opacity="0.92"/>'
            f'<text x="{lx}" y="{ly + 1}" text-anchor="middle" font-family="{FONT}"'
            f' font-size="11" fill="{MUTED}">{escape(label)}</text>'
        )
    return "\n".join(out)


def text(x, y, s, size=12, weight="400", fill=INK, anchor="start", font=FONT, opacity=1.0) -> str:
    size = max(size, MIN_FONT)
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" font-size="{size}"'
        f' font-weight="{weight}" fill="{fill}" opacity="{opacity}">{escape(s)}</text>'
    )


def chip(x, y, label, color, w=None, h=24) -> str:
    w = w or (len(label) * 7.0 + 22)
    return (
        f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{color}"'
        f' opacity="0.12"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}"'
        f' fill="none" stroke="{color}" stroke-width="1.2"/>'
        f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" font-family="{MONO}"'
        f' font-size="10.5" font-weight="600" fill="{color}">{escape(label)}</text></g>'
    )


def card(x, y, w, h, fill=PANEL, stroke="#D5DBE1") -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}"'
        f' stroke="{stroke}" stroke-width="1.3"/>'
    )


def svg(width, height, title, subtitle, body) -> str:
    # No fixed width/height on purpose.
    #
    # With them, a browser renders the SVG at its intrinsic size and stops. On a
    # wide page that means a 1010px diagram marooned in a 2500px column, which is
    # exactly how these looked on GitHub: technically correct, practically
    # unreadable.
    #
    # viewBox alone makes it fluid — it scales to whatever container it lands in,
    # and the aspect ratio is preserved. max-width stops it becoming grotesque on
    # an ultrawide monitor.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     preserveAspectRatio="xMidYMid meet"
     style="width:100%;height:auto;max-width:{width * 1.6:.0f}px"
     role="img" aria-label="{escape(title)}">
  <title>{escape(title)}</title>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/>
    </marker>
  </defs>
  <rect width="{width}" height="{height}" fill="{PAPER}"/>
  {text(28, 38, title, size=19, weight="700")}
  {text(28, 58, subtitle, size=12, fill=MUTED)}
{body}
</svg>
"""


# ------------------------------------------------------------------- diagrams


def d_reference_architecture() -> str:
    b = []
    b.append(boundary(28, 78, 1124, 690, "AWS CLOUD", "#232F3E", dashed=False))
    b.append(boundary(44, 100, 760, 480, "REGION", C_MGMT))
    b.append(boundary(60, 124, 728, 440, "VPC  \u00b7  private-by-default", C_NETWORK))

    b.append(boundary(76, 152, 696, 118, "PUBLIC SUBNET  (ingress only)", C_NETWORK, fill="#F3EEFF"))
    b.append(icon("igw", 100, 182, "Internet GW"))
    b.append(icon("waf", 240, 182, "WAF", "geo-blocking"))
    b.append(icon("alb", 380, 182, "ALB", "OIDC required"))
    b.append(icon("natgw", 540, 182, "NAT GW", "egress only"))
    b.append(arrow(150, 206, 238, 206))
    b.append(arrow(290, 206, 378, 206))

    b.append(boundary(76, 314, 696, 230, "PRIVATE SUBNETS  (multi-AZ)", C_NETWORK, fill="#F7FBF3"))
    b.append(boundary(92, 340, 430, 180, "EKS CLUSTER  \u00b7  private endpoint", C_CONTAINER))
    b.append(icon("eks", 116, 370, "Control plane", "audit logs on"))
    b.append(icon("ec2", 250, 370, "EC2 node", "IRSA, no keys"))
    b.append(icon("ec2", 384, 370, "EC2 node", "IRSA, no keys"))
    b.append(text(108, 500, "Pod security standards \u00b7 network policies \u00b7 "
                            "secrets envelope encryption", size=10, fill=MUTED))
    b.append(icon("lambda", 560, 370, "Lambda", "evidence collector"))
    b.append(icon("dynamodb", 672, 370, "DynamoDB", "findings, PITR"))

    b.append(arrow(404, 270, 320, 366))
    b.append(text(414, 296, "authenticated only", size=10, fill=MUTED))
    b.append(arrow(564, 340, 564, 272))
    b.append(text(576, 296, "egress", size=10, fill=MUTED))

    b.append(boundary(820, 100, 332, 480, "SECURITY & GOVERNANCE", C_SECURITY))
    b.append(icon("cloudtrail", 848, 132, "CloudTrail", "multi-region"))
    b.append(icon("s3lock", 990, 132, "S3 Object Lock", "COMPLIANCE"))
    b.append(icon("kms", 848, 240, "KMS CMK", "rotation on"))
    b.append(icon("sns", 990, 240, "SNS", "encrypted"))
    b.append(icon("iam", 848, 348, "IAM boundary", "AC-6 ceiling"))
    b.append(icon("cloudwatch", 990, 348, "CloudWatch", "metric filters"))
    b.append(arrow(898, 156, 986, 156))
    b.append(arrow(1014, 206, 1014, 238))
    b.append(arrow(1014, 314, 1014, 346))
    b.append(arrow(898, 264, 986, 264, dashed=True))

    b.append(arrow(790, 528, 846, 528))
    b.append(text(766, 522, "audit + telemetry", size=10, fill=MUTED, anchor="end"))

    b.append(card(844, 448, 292, 110))
    b.append(text(860, 472, "Evidence is a by-product", size=11.5, weight="700"))
    b.append(text(860, 492, "Object Lock COMPLIANCE cannot be bypassed", size=9.5, fill=MUTED))
    b.append(text(860, 506, "\u2014 not by a privileged role, not by root.", size=9.5, fill=MUTED))
    b.append(text(860, 520, "GOVERNANCE can. The mode is the control.", size=9.5, fill=MUTED))
    b.append(chip(860, 530, "AU-9  \u00b7  AU-11", C_SECURITY))

    b.append(boundary(44, 584, 760, 160, "ON-PREMISE  /  LAB SEGMENT", C_ONPREM))
    b.append(icon("router", 76, 614, "Edge router"))
    b.append(icon("firewall", 200, 614, "Firewall", "default deny"))
    b.append(icon("switch", 324, 614, "L3 switch", "VLAN trunk"))
    b.append(icon("vgw", 470, 614, "VPN gateway", "IPsec, multi-AZ"))
    b.append(arrow(150, 638, 198, 638))
    b.append(arrow(274, 638, 322, 638))
    b.append(arrow(398, 638, 468, 638))
    b.append(arrow(494, 612, 494, 548))
    b.append(text(506, 578, "encrypted transit", size=10, fill=MUTED))
    b.append(text(600, 634, "Segmented VLANs. The lab segment", size=10, fill=MUTED))
    b.append(text(600, 648, "reaches monitoring and nothing else.", size=10, fill=MUTED))

    b.append(text(28, 794, "Every module declares its controls in controls.yaml; "
                           "docs/control-coverage.md is generated from them.",
                  size=10.5, fill=MUTED))
    return svg(1180, 820, "Reference architecture",
               "FedRAMP Moderate-aligned AWS foundation \u00b7 written from public standards, "
               "no employer environment described", "\n".join(b))


def d_threat_model() -> str:
    b = []
    b.append(text(28, 82, "Attacks concentrate where the level of trust changes, because that is "
                          "where an assumption gets made.", size=11, fill=MUTED))

    # Actors
    b.append(boundary(28, 104, 178, 300, "UNTRUSTED", C_SECURITY, fill="#FDF2F4"))
    b.append(icon("github", 70, 140, "Internet", "anonymous"))
    b.append(icon("model", 70, 240, "Model output", "assume\u00a0compromised"))
    b.append(text(48, 340, "A customer-uploaded", size=9.5, fill=MUTED))
    b.append(text(48, 353, "document is untrusted", size=9.5, fill=MUTED))
    b.append(text(48, 366, "input, not content.", size=9.5, fill=MUTED))

    # Boundary column
    boundaries = [
        ("B1", 130, "Internet to edge", "the caller is who they claim to be", "T4"),
        ("B2", 200, "App to embedding store", "the query is scoped to the caller's tenant", "T1"),
        ("B3", 270, "Model to tool gate", "model output is a request, not a decision", "T2 T5"),
        ("B4", 340, "CI to cloud", "the pipeline runs the code we reviewed", "T4 T8"),
    ]
    for bid, y, name, assumption, threats in boundaries:
        b.append(card(236, y - 22, 470, 56, fill=PAPER))
        b.append(chip(248, y - 12, bid, C_NETWORK, w=34))
        b.append(text(294, y - 2, name, size=11.5, weight="700"))
        b.append(text(294, y + 14, assumption, size=9.5, fill=MUTED))
        b.append(text(694, y + 4, threats, size=9.5, weight="700", fill=BAD, anchor="end"))
        b.append(arrow(206, y, 232, y))

    b.append(text(236, 386, "The assumption is the thing to attack. Written down, a wrong one is "
                            "obvious to people who are not", size=9.5, fill=MUTED))
    b.append(text(236, 399, "security specialists — which is the audience most likely to know it "
                            "is false.", size=9.5, fill=MUTED))

    # Protected assets
    b.append(boundary(736, 104, 336, 300, "PROTECTED", C_STORAGE, fill="#F7FBF3"))
    assets = [
        ("vector", 132, "Customer documents", "one leak ends a contract"),
        ("s3lock", 214, "Audit records", "the only evidence there is"),
        ("iam", 296, "Deploy credentials", "control of the platform"),
    ]
    for ic, y, name, why in assets:
        b.append(icon(ic, 762, y, "", size=40))
        b.append(text(816, y + 16, name, size=11.5, weight="700"))
        b.append(text(816, y + 31, why, size=9.5, fill=MUTED))
    b.append(arrow(706, 200, 756, 160))
    b.append(arrow(706, 270, 756, 240))
    b.append(arrow(706, 340, 756, 320))

    # The signature threat
    b.append(card(28, 424, 1044, 76, fill="#FDF6EC", stroke="#E8C89A"))
    b.append(text(48, 448, "T6 — the one that is not on the diagram", size=12.5, weight="700"))
    b.append(text(48, 468, "A control that reports nothing and a control that finds nothing produce "
                           "identical output: silence. It has no arrow because it", size=10.5, fill=INK))
    b.append(text(48, 484, "is not a path through the system — it is every other arrow quietly "
                           "ceasing to be enforced. Found four times in this repo's own code.",
                  size=10.5, fill=INK))

    return svg(1100, 530, "Threat model — trust boundaries",
               "Each boundary states the assumption being made. The threats that attack it are "
               "named on the right.", "\n".join(b))


def d_data_flow() -> str:
    """Where data moves, and what protects it on each hop."""
    b = []
    b.append(text(28, 82, "Every arrow is a hop. Every hop names what protects it in transit and "
                          "what authorises it.", size=11, fill=MUTED))

    b.append(boundary(28, 104, 712, 116, "PUBLIC", C_SECURITY, fill="#FDF2F4"))
    b.append(icon("github", 60, 128, "Browser", "untrusted"))
    b.append(icon("waf", 250, 128, "WAF", "geo + rate"))
    b.append(icon("alb", 440, 128, "Edge", "OIDC required"))
    b.append(arrow(116, 152, 246, 152))
    b.append(text(181, 144, "TLS 1.2+", size=9, fill=MUTED, anchor="middle"))
    b.append(arrow(306, 152, 436, 152))
    b.append(text(371, 144, "geo-checked", size=9, fill=MUTED, anchor="middle"))

    b.append(boundary(28, 252, 712, 116, "APPLICATION", C_NETWORK, fill="#F3EEFF"))
    b.append(icon("eks", 60, 276, "API pod", "IRSA, no keys"))
    b.append(icon("model", 250, 276, "Retrieval", "tenant pre-filter"))
    b.append(icon("gate", 440, 276, "Tool gate", "session scopes"))
    b.append(icon("lambda", 620, 276, "Evidence job", "scheduled"))
    b.append(arrow(464, 220, 96, 272))
    b.append(text(300, 240, "OIDC session, not a header", size=9, fill=MUTED, anchor="middle"))
    b.append(arrow(116, 300, 246, 300))
    b.append(text(181, 292, "in-process", size=9, fill=MUTED, anchor="middle"))
    b.append(arrow(306, 300, 436, 300))
    b.append(text(371, 292, "typed allowlist", size=9, fill=MUTED, anchor="middle"))

    b.append(boundary(28, 400, 712, 122, "DATA", C_STORAGE, fill="#F7FBF3"))
    b.append(icon("vector", 250, 424, "Embedding store", "tenant partition"))
    b.append(icon("dynamodb", 440, 424, "Findings", "PITR"))
    b.append(icon("s3lock", 620, 424, "Audit store", "Object Lock"))
    b.append(icon("kms", 60, 424, "KMS", "envelope keys"))
    b.append(arrow(274, 348, 274, 420))
    b.append(text(284, 384, "pre-filter, then verify", size=9, fill=MUTED))
    b.append(arrow(644, 348, 644, 420))
    b.append(text(654, 384, "append only", size=9, fill=MUTED))
    b.append(arrow(636, 300, 476, 420))
    b.append(text(536, 366, "normalised", size=9, fill=MUTED))
    b.append(arrow(108, 448, 246, 448, dashed=True))
    b.append(text(177, 442, "data keys", size=9, fill=MUTED, anchor="middle"))

    b.append(card(764, 252, 388, 270))
    b.append(text(782, 278, "What is actually being protected", size=12.5, weight="700"))
    rows = [
        ("Customer content", "one leak ends a contract", BAD),
        ("Credentials", "none at rest \u2014 federated identity only", C_SECURITY),
        ("Audit records", "immutable for the retention window", OK),
        ("Telemetry", "carries no customer content by construction", MUTED),
    ]
    for i, (name, why, col) in enumerate(rows):
        y = 304 + i * 44
        b.append(text(782, y, name, size=11, weight="700", fill=col))
        b.append(text(782, y + 15, why, size=9.5, fill=MUTED))
    b.append(text(782, 494, "A classification nobody can act on is decoration.", size=9.5,
                  fill=MUTED))
    b.append(text(782, 508, "Each line here changes a control decision.", size=9.5, fill=MUTED))

    b.append(text(28, 556, "The hop with no label is the one to ask about. An unlabelled arrow "
                           "usually means nobody decided \u2014 not that nothing applies.",
                  size=10, fill=INK))
    return svg(1180, 580, "Data flow and protection",
               "A data-flow diagram is only useful if each flow names its control. "
               "Otherwise it is a picture of boxes.", "\n".join(b))


def d_review_triage() -> str:
    """What needs a security review, and what does not."""
    b = []
    b.append(text(28, 82, "Reviewing everything and reviewing nothing fail the same way: the "
                          "reviewer becomes a formality. This is the line.", size=11, fill=MUTED))

    b.append(icon("github", 44, 150, "A change", "arrives"))

    lanes = [
        ("BLOCKING REVIEW", 108, BAD, "#FDF2F4",
         ["IAM policy, role or trust policy",
          "Network path, security group, ingress",
          "Authentication or authorisation logic",
          "Cryptography, key handling, secrets",
          "A new data flow or a new store",
          "CI workflow or a gate definition",
          "Anything an agent can invoke"],
         "Merge blocked until fixed, or accepted in writing",
         "with a named owner, a compensating control and an expiry."),
        ("ADVISORY", 344, "#B7791F", "#FDF6EC",
         ["New dependency, no new capability",
          "Config change inside existing bounds",
          "Refactor with no interface change",
          "Observability and logging additions"],
         "Comments, no hold. Escalates only if the review",
         "turns up something from the list above."),
        ("NO REVIEW", 524, OK, "#F3FAF3",
         ["Tests, fixtures, documentation",
          "Formatting, lint, comments",
          "Generated artifacts, regenerated"],
         "CI still runs every gate.",
         "No human in the path."),
    ]
    for name, y, col, fill, items, note1, note2 in lanes:
        h = 44 + len(items) * 19 + 44
        b.append(boundary(232, y, 546, h, name, col, fill=fill))
        for i, it in enumerate(items):
            b.append(text(252, y + 46 + i * 19, "\u2022  " + it, size=10.5, fill=INK))
        base = y + 46 + len(items) * 19
        b.append(text(252, base + 14, note1, size=9.5, fill=MUTED))
        b.append(text(252, base + 28, note2, size=9.5, fill=MUTED))
        b.append(arrow(112, 174, 228, y + h / 2, curve=10))

    b.append(card(802, 108, 350, 212))
    b.append(text(820, 134, "Why the line sits here", size=12.5, weight="700"))
    for i, line in enumerate([
        "The blocking list is not a list of important",
        "things. It is the list of changes where a",
        "mistake is silent and expensive to reverse.",
    ]):
        b.append(text(820, 158 + i * 15, line, size=10, fill=MUTED))
    for i, line in enumerate([
        "A wildcard in a trust policy looks correct",
        "in review, and hands the deploy role to",
        "anyone who can push a branch.",
    ]):
        b.append(text(820, 218 + i * 15, line, size=10, fill=INK))
    b.append(chip(820, 278, "56% of reviewed PRs were held", BAD, w=250))

    b.append(card(802, 344, 350, 240))
    b.append(text(820, 370, "A blocking finding clears two ways", size=12.5, weight="700"))
    b.append(chip(820, 386, "1   fixed", OK, w=100))
    b.append(chip(820, 424, "2   accepted in writing", "#B7791F", w=200))
    for i, line in enumerate([
        "An acceptance names an owner, a compensating",
        "control and an expiry, and re-opens the finding",
        "when it lapses.",
    ]):
        b.append(text(820, 476 + i * 15, line, size=10, fill=MUTED))
    for i, line in enumerate([
        "There is no third path. \"We will fix it next",
        "sprint\" is not a disposition, and a reviewer who",
        "accepts it has moved the line.",
    ]):
        b.append(text(820, 530 + i * 15, line, size=10, fill=BAD))

    return svg(1180, 700, "What needs a security review",
               "Published so engineers can self-serve the answer, and so a hold is never a "
               "surprise.", "\n".join(b))


def d_standards_to_code() -> str:
    """How a written standard becomes an enforced control."""
    b = []
    b.append(text(28, 82, "A standard is a sentence. A control is a thing that stops something. "
                          "These are the steps between, and each one can silently fail.",
                  size=11, fill=MUTED))

    # The chip is coloured by SPACE, not by stage. The whole point of the
    # diagram is where architecture hands off to engineering, so that boundary
    # has to be visible at a glance rather than inferred from the labels.
    SPACE = {"architecture": C_MGMT, "engineering": C_COMPUTE, "assessment": C_STORAGE}
    stages = [
        ("report", "Standard", "NIST 800-53 Rev 5\nFedRAMP Moderate", "architecture"),
        ("iam", "Decision", "which controls apply,\nand why", "architecture"),
        ("ec2", "Module", "Terraform that\nimplements it", "engineering"),
        ("gate", "Gate", "CI blocks the\nregression", "engineering"),
        ("s3lock", "Evidence", "generated, dated,\nattributable", "assessment"),
    ]
    x = 44
    for i, (ic, title, sub, space) in enumerate(stages):
        b.append(card(x, 116, 190, 150))
        b.append(icon(ic, x + 16, 136, "", size=42))
        b.append(text(x + 70, 158, title, size=13, weight="700"))
        for j, line in enumerate(sub.split("\n")):
            b.append(text(x + 70, 176 + j * 13, line, size=9.5, fill=MUTED))
        b.append(chip(x + 16, 228, space, SPACE[space], w=158))
        if i < len(stages) - 1:
            b.append(arrow(x + 194, 190, x + 232, 190))
        x += 232

    b.append(f'<path d="M508,110 L508,272" stroke="{INK}" stroke-width="1.4" '
             f'stroke-dasharray="5 4" opacity="0.55"/>')
    b.append(text(508, 288, "architecture  \u2192  engineering", size=10, weight="700",
                  fill=INK, anchor="middle"))
    b.append(text(44, 300, "What is lost if the step is skipped", size=12.5, weight="700"))
    losses = [
        (44, "Nothing applies.", "A baseline nobody scoped is a\nreading list."),
        (276, "It is documented.", "An architecture record with no\nmodule is an intention."),
        (508, "It is deployed.", "Correct on the day it merged.\nDrift is invisible."),
        (740, "It is enforced.", "Until the gate stops running and\nreports success anyway."),
        (972, "It is provable.", "Without this the other four are\nreconstructed before an audit."),
    ]
    for x0, head, body in losses:
        b.append(text(x0, 326, head, size=10.5, weight="700", fill=INK))
        for j, line in enumerate(body.split("\n")):
            b.append(text(x0, 344 + j * 13, line, size=9.5, fill=MUTED))

    b.append(card(44, 392, 1092, 96, fill="#FDF6EC", stroke="#E8C89A"))
    b.append(text(64, 418, "The join that usually breaks", size=12.5, weight="700"))
    b.append(text(64, 440, "Between DECISION and MODULE the language changes \u2014 a control "
                           "family becomes a resource argument \u2014 and nothing checks the "
                           "translation.", size=10.5, fill=INK))
    b.append(text(64, 458, "Here each module declares its controls next to the code, every claim "
                           "names its EVIDENCE, and CI fails if a module has Terraform and no "
                           "declaration.", size=10.5, fill=INK))
    b.append(text(64, 476, "The mapping moves with the code, or it is not a mapping.",
                  size=10.5, weight="700", fill=INK))

    return svg(1180, 520, "From standard to enforced control",
               "Architecture space to engineering space, and the evidence that survives the "
               "trip.", "\n".join(b))


def d_scanner_sequence() -> str:
    """When each class of scanner can run, and what it can see."""
    b = []
    b.append(text(28, 82, "Each scanner runs at the earliest point its problem can be detected. "
                          "The cost of fixing rises at every stage to the right.",
                  size=11.5, fill=MUTED))

    stages = [
        ("Commit", 44, "gitleaks", "secrets", C_SECURITY,
         "A committed key is already", "an incident. Nothing else", "is true at this stage."),
        ("Pull request", 268, "semgrep \u00b7 bandit", "SAST", C_DEVTOOLS,
         "Cheapest place to fix:", "the author still has", "the context."),
        ("Pull request", 492, "checkov \u00b7 tfsec", "IaC", C_NETWORK,
         "Before apply, a fix is", "a text edit. After, it is", "change management."),
        ("Build", 716, "trivy", "container + deps", C_COMPUTE,
         "Needs artifacts that do", "not exist until now \u2014 a", "resolved tree, an image."),
        ("Deployed", 940, "Security Hub", "CSPM \u00b7 ASFF", C_MGMT,
         "The only one that sees", "REALITY rather than a", "description of it."),
    ]
    for label, x, tools, cat, col, l1, l2, l3 in stages:
        b.append(card(x, 116, 196, 250))
        b.append(chip(x + 14, 130, label, col, w=168))
        b.append(text(x + 14, 182, tools, size=13, weight="700", font=MONO))
        b.append(text(x + 14, 202, cat, size=11, fill=MUTED))
        for i, line in enumerate((l1, l2, l3)):
            b.append(text(x + 14, 236 + i * 16, line, size=10.5, fill=INK))
        b.append(chip(x + 14, 322, "cost to fix: " + ("low" if x < 500 else "higher"),
                      OK if x < 500 else "#B7791F", w=168))

    for x in (240, 464, 688, 912):
        b.append(arrow(x, 240, x + 26, 240))

    b.append(card(44, 400, 1092, 116, fill="#FDF2F4", stroke="#E8B4BC"))
    b.append(text(64, 426, "What none of them catch", size=13, weight="700", fill=BAD))
    misses = [
        "Business logic flaws \u2014 \"users can refund twice\" is not a pattern",
        "Authorization design errors \u2014 a correct-looking check on the WRONG object passes every rule",
        "MISSING controls \u2014 scanners find bad configuration, not absent configuration",
        "A control that stopped running \u2014 a scanner registering zero rules reports a clean scan",
    ]
    for i, m in enumerate(misses):
        b.append(text(64, 450 + i * 16, "\u2022  " + m, size=10.5, fill=INK))

    b.append(text(28, 548, "Scanners raise the floor. Threat modelling and human review raise the "
                           "ceiling \u2014 which is why both are in this repository.",
                  size=11, weight="700", fill=INK))
    return svg(1180, 572, "Scanner sequencing",
               "Seven tools, five stages. What each can see, and when it can possibly see it.",
               "\n".join(b))


def d_ci_pipeline() -> str:
    b = []
    b.append(icon("github", 44, 118, "Pull request", "or push to main"))

    jobs = [
        ("scanner", "hygiene", "no career or\ncredential material"),
        ("gate", "policies", "custom checks\nload AND fire"),
        ("report", "control mapping", "evidence declared,\nreport not stale"),
        ("ec2", "terraform", "fmt + validate,\nevery module"),
        ("iam", "security scan", "checkov soft_fail\n= false"),
        ("scanner", "normalizer e2e", "gate must exit\nnon-zero"),
    ]
    x0, y0 = 224, 96
    for i, (ic, name, note) in enumerate(jobs):
        col, row = i % 3, i // 3
        x = x0 + col * 250
        y = y0 + row * 168
        b.append(card(x, y, 214, 138))
        b.append(icon(ic, x + 16, y + 16, "", size=40))
        b.append(text(x + 68, y + 34, name, size=12.5, weight="700"))
        for j, line in enumerate(note.split("\n")):
            b.append(text(x + 68, y + 50 + j * 13, line, size=10, fill=MUTED))
        b.append(chip(x + 16, y + 100, "must pass", OK))
        b.append(arrow(140, 160, x - 6, y + 60, curve=(row - 0.5) * 40) if col == 0 else "")

    for row in range(2):
        for col in range(2):
            x = x0 + col * 250 + 214
            y = y0 + row * 168 + 60
            b.append(arrow(x, y, x + 36, y))

    b.append(icon("gate", 990, 200, "Merge gate", "all must pass"))
    b.append(arrow(938, 164, 986, 210, curve=-14))
    b.append(arrow(938, 332, 986, 262, curve=14))

    b.append(card(44, 452, 900, 118))
    b.append(text(62, 476, "Why the last job asserts a FAILURE", size=13, weight="700"))
    b.append(text(62, 498,
                  "normalizer-gate ingests fixtures containing CRITICAL findings and requires "
                  "the gate to exit non-zero.", size=11, fill=MUTED))
    b.append(text(62, 514,
                  "A gate nobody has watched fail is a gate nobody knows works — and a gate that "
                  "silently stopped matching", size=11, fill=MUTED))
    b.append(text(62, 530,
                  "reports exactly the same green tick as one that is working.", size=11, fill=MUTED))
    b.append(chip(62, 540, "see docs/silent-failure-patterns.md", C_SECURITY))

    b.append(text(1014, 312, "merge", size=11, weight="700", fill=OK, anchor="middle"))
    b.append(text(1014, 328, "or block", size=11, weight="700", fill=BAD, anchor="middle"))
    return svg(1100, 600, "CI gates",
               "Six jobs, all blocking. Every exception is inline and reasoned; "
               "soft_fail is never used.", "\n".join(b))


def d_findings_pipeline() -> str:
    b = []
    tools = ["trivy", "checkov", "tfsec", "semgrep", "bandit", "gitleaks", "asff"]
    for i, t in enumerate(tools):
        y = 96 + i * 58
        b.append(icon("scanner", 44, y, "", size=34))
        b.append(text(88, y + 22, t, size=12, weight="600", font=MONO))
    b.append(boundary(28, 78, 160, 424, "SCANNERS", C_DEVTOOLS))
    b.append(text(40, 492, "7 parsers, 7 fixtures", size=10, fill=MUTED))

    b.append(card(232, 96, 250, 172))
    b.append(text(250, 122, "Normalize", size=13.5, weight="700"))
    b.append(text(250, 144, "identity =", size=10.5, fill=MUTED, font=MONO))
    b.append(text(250, 160, "sha256(tool_class, rule_id,", size=10, fill=INK, font=MONO))
    b.append(text(250, 174, "         file_path, resource_id)", size=10, fill=INK, font=MONO))
    b.append(text(250, 198, "Excluded deliberately:", size=10.5, fill=MUTED))
    b.append(text(250, 213, "line numbers · timestamps ·", size=10, fill=INK))
    b.append(text(250, 227, "vendor rule names · remediation text", size=10, fill=INK))
    b.append(chip(250, 238, "survives a re-scan", C_DEVTOOLS))

    b.append(card(232, 300, 250, 126))
    b.append(text(250, 326, "Merge across tools", size=13.5, weight="700"))
    b.append(text(250, 348, "tfsec and Trivy share a rule DB and", size=10, fill=MUTED))
    b.append(text(250, 362, "both report AVD-AWS-0107 — one", size=10, fill=MUTED))
    b.append(text(250, 376, "finding, two attributions.", size=10, fill=MUTED))
    b.append(chip(250, 390, "20 parsed → 19 tracked", C_STORAGE))

    b.append(icon("dynamodb", 560, 150, "Append-only store", "observation log"))
    b.append(card(536, 232, 220, 132))
    b.append(text(554, 256, "A fold, not an overwrite", size=12, weight="700"))
    b.append(text(554, 276, "first_seen · last_seen · age", size=10, fill=MUTED))
    b.append(text(554, 292, "regression: fixed, then back", size=10, fill=MUTED))
    b.append(text(554, 308, "acceptance expiry re-blocks", size=10, fill=MUTED))
    b.append(text(554, 330, "An overwriting store cannot", size=10, fill=BAD))
    b.append(text(554, 344, "answer 'did it come back?'", size=10, fill=BAD))

    b.append(icon("gate", 856, 116, "CI gate", "--fail-on critical,high"))
    b.append(icon("report", 856, 246, "HTML report", "self-contained"))

    b.append(arrow(190, 260, 228, 180, curve=-20))
    b.append(arrow(357, 268, 357, 296))
    b.append(arrow(486, 200, 556, 176))
    b.append(arrow(486, 360, 556, 300))
    b.append(arrow(760, 190, 852, 150))
    b.append(arrow(760, 300, 852, 280))

    b.append(card(536, 396, 400, 84))
    b.append(text(554, 420, "The gitleaks parser never reads Secret or Match", size=11.5,
                  weight="700", fill=BAD))
    b.append(text(554, 440, "A normalizer that copies the matched credential has taken a leak",
                  size=10, fill=MUTED))
    b.append(text(554, 454, "in one place and written it to a second one. There is a test.",
                  size=10, fill=MUTED))
    return svg(1010, 520, "Findings normalization",
               "Scanner sprawl into one system of record with stable identity, "
               "history and ownership", "\n".join(b))


def d_ai_security() -> str:
    b = []
    b.append(boundary(28, 78, 470, 400, "RETRIEVAL BOUNDARY", C_DATABASE))
    b.append(text(48, 112, "Three designs, and the interesting one is not the leak",
                  size=12, weight="700"))

    rows = [
        ("Leaky", "rank globally, caller filters", BAD, "leaks", BAD),
        ("Starved", "rank globally, then filter", "#B7791F", "no leak — and no results", "#B7791F"),
        ("Isolated", "predicate BEFORE ranking", OK, "correct, and verified after", OK),
    ]
    for i, (name, how, color, verdict, vc) in enumerate(rows):
        y = 134 + i * 108
        b.append(card(48, y, 430, 92, fill=PAPER))
        b.append(icon("vector", 64, y + 20, "", size=40))
        b.append(text(118, y + 30, name, size=13, weight="700", fill=color))
        b.append(text(118, y + 48, how, size=10.5, fill=MUTED))
        b.append(chip(118, y + 58, verdict, vc))

    b.append(text(48, 462, "A leak test passes on Starved. Only a lopsided corpus finds it.",
                  size=10, fill=MUTED))

    b.append(boundary(522, 78, 458, 400, "TOOL AUTHORIZATION", C_SECURITY))
    b.append(icon("model", 546, 112, "Model", "assume compromised"))
    b.append(arrow(614, 136, 700, 136, "tool call"))

    b.append(card(700, 100, 260, 250, fill=PAPER))
    b.append(text(716, 124, "Gate — deterministic code", size=12, weight="700"))
    rules = [
        "1  deny by default",
        "2  scopes from the session",
        "3  subject-bound args must match",
        "4  egress host allowlisted",
        "5  irreversible needs bound token",
    ]
    for i, r in enumerate(rules):
        b.append(text(716, 150 + i * 22, r, size=10.5, fill=INK, font=MONO))
    b.append(chip(716, 268, "no input reachable from the prompt", C_SECURITY, w=228))
    b.append(text(716, 314, "Same control as tenant isolation,", size=10, fill=MUTED))
    b.append(text(716, 328, "enforced at the tool boundary.", size=10, fill=MUTED))

    b.append(arrow(830, 350, 830, 386))
    b.append(chip(700, 392, "ALLOW · 2 baselines", OK, w=136))
    b.append(chip(852, 392, "DENY · 11 cases", BAD, w=118))
    b.append(text(546, 442, "No LLM call anywhere. A test whose expected output is",
                  size=10, fill=MUTED))
    b.append(text(546, 456, "model-generated gets quarantined the first time it flakes.",
                  size=10, fill=MUTED))
    return svg(1010, 500, "AI security controls",
               "Assume the model is already fully compromised, then ask what still holds",
               "\n".join(b))


def d_two_lanes() -> str:
    """Two scanning lanes writing one record: an automated CI lane and a local
    compensating-control lane that exists before it is needed."""
    b = []
    b.append(text(28, 80, "Scanning capability is itself a control — and controls have "
                          "availability requirements.", size=11, fill=MUTED))
    b.append(text(28, 96, "Lane 2 is the same tools behind one script: a compensating control "
                          "that exists before it is needed.", size=11, fill=MUTED))

    def step(x, y, w, title, sub):
        return "\n".join([
            card(x, y, w, 52),
            text(x + 16, y + 22, title, size=11.5, weight="700"),
            text(x + 16, y + 39, sub, size=9.5, fill=MUTED),
        ])

    lanes = [
        (44, "LANE 1 · CI PIPELINE  (automated)", C_DEVTOOLS, "#F6F3FF", 74, [
            ("Triggers", "PR · push · nightly schedule"),
            ("Scan jobs — one per surface", "fan out in parallel"),
            ("Findings writer", "one schema for every tool"),
            ("Merge gate", "reads the store, blocks on policy"),
        ]),
        (626, "LANE 2 · LOCAL RUNNER  (compensating control)", C_STORAGE, "#F7FBF3", 656, [
            ("One script, zero arguments", "runs on any laptop"),
            ("The same tools, pinned versions", "identical coverage"),
            ("Evidence directory per run", "SUMMARY · manifest · raw · logs"),
            ("Run-over-run delta", "every count move gets a named cause"),
        ]),
    ]
    for bx, title, col, fill, cx, steps in lanes:
        b.append(boundary(bx, 116, 490, 372, title, col, fill=fill))
        y = 150
        for i, (t, s) in enumerate(steps):
            b.append(step(cx, y, 430, t, s))
            if i < len(steps) - 1:
                b.append(arrow(cx + 215, y + 52, cx + 215, y + 82))
            y += 84

    b.append(arrow(534, 300, 626, 300, dashed=True))
    b.append(text(580, 272, "when lane 1 is down,", size=9.5, fill=MUTED, anchor="middle"))
    b.append(text(580, 286, "lane 2 IS the record", size=10, weight="700", fill=INK, anchor="middle"))

    b.append(card(385, 508, 400, 54, fill="#EEF4FF", stroke="#B9C7E6"))
    b.append(text(585, 532, "Findings store — one system of record", size=12,
                  weight="700", anchor="middle"))
    b.append(text(585, 549, "both lanes write here; a scan you can't prove ran is no scan",
                  size=9.5, fill=MUTED, anchor="middle"))
    b.append(arrow(289, 454, 430, 506))
    b.append(arrow(871, 454, 740, 506))

    return svg(1160, 600, "Two lanes, one record",
               "An automated CI lane and a local compensating-control lane, writing one "
               "system of record.", "\n".join(b))


def d_integrity_loop() -> str:
    """The canary/floor/delta loop that turns a clean scan into evidence."""
    b = []
    b.append(text(28, 80, "A scanner that runs and finds nothing must be distinguishable from "
                          "one that was never looking.", size=11, fill=MUTED))
    b.append(text(28, 96, "Every run clears this loop before its results count as evidence — "
                          "it costs seconds, and has caught real failures.", size=11, fill=MUTED))

    def node(x, y, title, sub, fill=PANEL, stroke="#D5DBE1", tcol=INK, w=156, h=58):
        out = [card(x, y, w, h, fill=fill, stroke=stroke),
               text(x + w / 2, y + 24, title, size=11.5, weight="700", fill=tcol, anchor="middle")]
        if sub:
            out.append(text(x + w / 2, y + 41, sub, size=9.5, fill=MUTED, anchor="middle"))
        return "\n".join(out)

    Y = 128
    b.append(node(40, Y, "Output produced", "a scanner ran"))
    b.append(node(240, Y, "Canary", "flagged its defect?"))
    b.append(node(440, Y, "Coverage floor", "scope ≥ baseline?"))
    b.append(node(640, Y, "Zero findings?", "files · checks · targets"))
    b.append(node(840, Y, "Delta vs last run", "did a count move?"))
    b.append(node(1040, Y, "Trustworthy record", "dated · diffable",
                  fill="#F3FAF3", stroke="#B6DFB6", tcol=OK))

    b.append(node(640, 250, "Zero enumerated?", "logs prove the scope"))
    b.append(node(300, 250, "RUN VOID", "clean results are not evidence",
                  fill="#FDF2F4", stroke="#E8B4BC", tcol=BAD, w=220))
    b.append(node(560, 356, "UNKNOWN", "treat as no scan, never clean",
                  fill="#FDF2F4", stroke="#E8B4BC", tcol=BAD, w=220))
    b.append(node(840, 250, "Name the cause", "code · DB · config · pollution", w=200))

    b.append(arrow(196, Y + 29, 240, Y + 29))
    b.append(arrow(396, Y + 29, 440, Y + 29, "flagged"))
    b.append(arrow(596, Y + 29, 640, Y + 29, "held"))
    b.append(arrow(796, Y + 29, 840, Y + 29, "findings"))
    b.append(arrow(996, Y + 29, 1040, Y + 29, "no move"))

    b.append(arrow(718, Y + 58, 718, 250, "zero"))
    b.append(arrow(796, 279, 840, 172, "enumerated"))
    b.append(arrow(318, Y + 58, 370, 250, "missed"))
    b.append(arrow(518, Y + 58, 470, 250, "shrank"))
    b.append(arrow(718, 308, 670, 356, "no"))
    b.append(arrow(918, Y + 58, 918, 250, "moved"))
    b.append(arrow(1000, 250, 1080, Y + 58))

    return svg(1200, 470, "The integrity loop",
               "\"The scanner ran\" and \"the scanner was looking\" are different claims. "
               "Only the second is evidence.", "\n".join(b))


def d_incident_response() -> str:
    """A swimlane IR process (originally drawn in 2017) remapped onto the current
    model: NIST 800-61r3 (2025) retired the linear lifecycle for the CSF 2.0
    functions — a continuous cycle with Govern wrapping it."""
    b = []
    b.append(text(28, 82, "A swimlane IR process I drew in 2017, remapped onto the current model. "
                          "NIST 800-61r3 (2025) retired the linear", size=11, fill=MUTED))
    b.append(text(28, 97, "four-phase lifecycle for the CSF 2.0 functions — a continuous cycle, "
                          "with Govern as a new overarching function.", size=11, fill=MUTED))

    # Govern wraps the whole cycle — the function the pre-r3 model did not have.
    b.append(boundary(28, 116, 1124, 224,
                      "GOVERN  ·  CSF 2.0 overarching function — new in 800-61r3, "
                      "absent from the old linear model", C_MGMT, fill="#FDF3F9"))

    # original phase -> CSF 2.0 / 800-61r3 function, owner lane, activity
    stages = [
        ("Prevention", "Identify · Protect", "Business + SOC",
         ["awareness, assessments,", "tooling, proactive monitoring"], C_STORAGE),
        ("Detection", "Detect", "SOC + Service Desk",
         ["detection capability;", "notice & log the event"], C_NETWORK),
        ("Classification", "Detect → Respond", "Service Desk + SOC",
         ["security triage;", "route the event"], C_NETWORK),
        ("Control & Eradication", "Respond", "SOC + Management",
         ["plan & execute the", "technical response"], C_SECURITY),
        ("Recovery & Follow-up", "Recover → Improve", "Management + SOC",
         ["restore service; AAR;", "share lessons"], C_COMPUTE),
    ]
    x = 44
    for i, (name, csf, owner, act, col) in enumerate(stages):
        b.append(card(x, 150, 194, 152, fill=PAPER))
        b.append(text(x + 14, 173, name, size=11.5, weight="700"))
        b.append(chip(x + 14, 183, csf, col, w=166))
        b.append(text(x + 14, 233, owner, size=10.5, weight="700", fill=INK))
        for j, ln in enumerate(act):
            b.append(text(x + 14, 251 + j * 14, ln, size=9.5, fill=MUTED))
        if i < len(stages) - 1:
            b.append(arrow(x + 194, 226, x + 224, 226))
        x += 224

    # the cycle closes — the single biggest change from the linear original
    b.append(arrow(1140, 316, 60, 316, "continuous — lessons feed prevention, not a dead end",
                   curve=16))

    b.append(text(28, 372, "Failure modes the loop exists to prevent", size=12, weight="700"))
    fails = [
        ("Detection with no consumer", "an alert nobody triages is noise, not detection", C_NETWORK),
        ("A response that leaves no record", "containment with no change log can't be audited or learned from", C_SECURITY),
        ("\"No AAR needed\" as a habit", "the improve loop that never closes — the old model's weakest link", C_MGMT),
    ]
    fx = 28
    for title, body_, col in fails:
        b.append(card(fx, 388, 362, 92, fill="#FDF6EC", stroke="#E8C89A"))
        b.append(text(fx + 16, 414, title, size=11.5, weight="700", fill=col))
        # wrap body to fit the card
        words, line, lines = body_.split(), "", []
        for w in words:
            if len(line + " " + w) > 52:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        for j, ln in enumerate(lines):
            b.append(text(fx + 16, 434 + j * 15, ln, size=10, fill=INK))
        fx += 384

    return svg(1180, 500, "Incident response — modernised lifecycle",
               "A 2017 swimlane process remapped onto NIST 800-61r3 / CSF 2.0. The "
               "responsibilities carry over; the framing is current.", "\n".join(b))


DIAGRAMS = {
    "reference-architecture": d_reference_architecture,
    "threat-model": d_threat_model,
    "scanner-sequence": d_scanner_sequence,
    "data-flow": d_data_flow,
    "review-triage": d_review_triage,
    "standards-to-code": d_standards_to_code,
    "ci-gates": d_ci_pipeline,
    "findings-pipeline": d_findings_pipeline,
    "ai-security": d_ai_security,
    "two-lanes": d_two_lanes,
    "integrity-loop": d_integrity_loop,
    "incident-response": d_incident_response,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=OUT_DIR, type=Path)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if committed SVGs differ from freshly rendered ones")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    stale = []
    for name, fn in DIAGRAMS.items():
        path = args.out / f"{name}.svg"
        rendered = fn()
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                stale.append(str(path))
        else:
            path.write_text(rendered, encoding="utf-8")
            print(f"wrote {path}")

    if args.check:
        if stale:
            print("diagram check FAILED · stale or missing:", file=sys.stderr)
            for s in stale:
                print(f"  {s}", file=sys.stderr)
            print("\nRegenerate:  python tools/render_diagrams.py", file=sys.stderr)
            return 1
        print(f"diagram check passed · {len(DIAGRAMS)} diagrams match their source")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
