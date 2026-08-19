"""This file must exist — and that is the entire point.

Checkov discovers custom checks by importing this package. Without an
``__init__.py`` here, the external-checks loader registers **zero** checks: the
scan completes normally, reports its usual counts, and CI goes green while
nothing is enforced. That silent fail-open is why this directory exists at all
(see the README).

Its presence is not left to trust. ``test_policy_registration.py`` asserts both
that the checks register *and* that removing this file breaks registration —
``mv checkov/__init__.py /tmp && pytest policies`` turns the suite red. An empty
but present file is load-bearing; this docstring is here so the next reader knows
that before they "tidy up" a blank file.
"""
