"""Parser registry.

Adding a scanner is one file implementing `parse(raw) -> list[Finding]`, plus one
line here. That constraint is deliberate: the moment normalization logic starts
living in the ingest path instead of the parser, every new tool becomes a change
to shared code and the cost of adding the eighth scanner is not the cost of
adding the second.
"""
from __future__ import annotations

from types import ModuleType

from . import asff, bandit, checkov, gitleaks, semgrep, tfsec, trivy

REGISTRY: dict[str, ModuleType] = {
    "asff": asff,
    "bandit": bandit,
    "checkov": checkov,
    "gitleaks": gitleaks,
    "semgrep": semgrep,
    "tfsec": tfsec,
    "trivy": trivy,
}

SUPPORTED = sorted(REGISTRY)

__all__ = ["REGISTRY", "SUPPORTED", "get"]


def get(tool: str) -> ModuleType:
    try:
        return REGISTRY[tool]
    except KeyError:
        raise KeyError(
            f"no parser for {tool!r}; supported: {', '.join(SUPPORTED)}"
        ) from None
