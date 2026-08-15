"""Tests for the generated diagrams.

Every defect these catch was previously found by rendering a PNG and looking at
it, which does not scale and does not run in CI. A diagram is the one artifact
in this repository that can be completely broken while remaining valid XML — so
the properties that make it *legible* are asserted here rather than trusted to
whoever last opened it.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from render_diagrams import DIAGRAMS, MIN_FONT

NS = "{http://www.w3.org/2000/svg}"
OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams"
SVGS = sorted(OUT.glob("*.svg"))

# Average advance width per em for the sans stack. Deliberately generous — this
# is a guard against real overflow, not a typesetter.
EM = 0.55


def _root(path: Path):
    return ET.parse(path).getroot()


def test_every_declared_diagram_was_written():
    """Guards the rest of this file: a missing SVG must fail loudly, not be
    silently skipped by a glob that found nothing."""
    assert SVGS, "no diagrams found on disk"
    names = {p.stem for p in SVGS}
    assert names == set(DIAGRAMS), f"declared {set(DIAGRAMS)} but found {names}"


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.stem)
def test_svg_is_fluid(path):
    """No fixed width/height on the root element.

    With them, a browser renders the SVG at its intrinsic size and stops — a
    1010px diagram marooned in a 2500px column, technically correct and
    practically unreadable. That is exactly how these looked on GitHub before
    the attributes were removed.
    """
    root = _root(path)
    assert root.get("viewBox"), "viewBox is what makes it scalable"
    assert root.get("width") is None, "a fixed width stops the diagram scaling to its container"
    assert root.get("height") is None, "a fixed height stops the diagram scaling"


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.stem)
def test_no_text_smaller_than_the_legibility_floor(path):
    """Anything under the floor reads as texture once a browser scales it down."""
    too_small = [
        (float(t.get("font-size")), "".join(t.itertext())[:40])
        for t in _root(path).iter(NS + "text")
        if t.get("font-size") and float(t.get("font-size")) < MIN_FONT
    ]
    assert not too_small, f"text below {MIN_FONT}px: {too_small[:3]}"


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.stem)
def test_no_text_runs_past_the_canvas(path):
    """Catches the failure mode that a font-size increase causes.

    Raising type in a fixed layout pushes the longest line off the right edge,
    and the SVG stays perfectly valid XML while doing it.
    """
    root = _root(path)
    width = float(root.get("viewBox").split()[2])
    overflows = []
    for t in root.iter(NS + "text"):
        txt = "".join(t.itertext())
        if not txt.strip():
            continue
        size = float(t.get("font-size", 12))
        w = len(txt) * size * EM
        x = float(t.get("x", 0))
        anchor = t.get("text-anchor", "start")
        left = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
        if left + w > width:
            overflows.append((round(left + w - width), txt[:40]))
    assert not overflows, f"text past the right edge by px: {overflows[:3]}"


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.stem)
def test_diagram_is_self_contained(path):
    """No external fetch, no script, no embedded raster.

    A diagram that needs a CDN renders blank inside the networks where this kind
    of material actually gets read, and a script in an SVG is a stored-XSS sink
    the moment anyone hosts it.
    """
    body = path.read_text(encoding="utf-8")
    external = [
        u for u in __import__("re").findall(r'https?://[^"\'\s>]+', body)
        if u != "http://www.w3.org/2000/svg"
    ]
    assert not external, f"external references: {external[:3]}"
    for forbidden in ("<script", "<image", "xlink:href", "<foreignObject"):
        assert forbidden not in body, f"contains {forbidden}"


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.stem)
def test_diagram_has_an_accessible_title(path):
    root = _root(path)
    assert root.get("role") == "img"
    assert root.get("aria-label"), "needs an aria-label for screen readers"
    assert root.find(NS + "title") is not None, "needs a <title> element"
