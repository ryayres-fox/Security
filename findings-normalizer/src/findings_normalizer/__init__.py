"""findings-normalizer — fold many scanners into one deduplicated, append-only
system of record with a stable per-finding identity.

Start at the package README for the design and usage. The moving parts:

- ``models``   — the ``Finding`` schema, the ``Severity``/``Disposition`` enums, the identity hash
- ``parsers/`` — one module per scanner (``parse(raw) -> list[Finding]``), listed in the registry
- ``store``    — the append-only ``Observation`` log and the fold to current state
- ``report``   — the self-contained HTML report
- ``cli``      — ``findings-normalize ingest | report | gate``
"""
