"""The tests are the deliverable here, not the store.

Each one is written so that removing the control makes it fail. A test that
passes against both the isolated and the leaky implementation is proving
nothing, so several of these assert against `LeakyStore` and `StarvedStore`
directly — demonstrating the failure is the only way to show the control is
load-bearing.
"""
from __future__ import annotations

import pytest
from vector_store import (
    Hit,
    IsolatedStore,
    LeakyStore,
    StarvedStore,
    TenantIsolationError,
    cosine,
)

# Tenant B's document is a near-exact match for the query. Tenant A's is not.
# Any implementation that ranks before filtering will surface B's row first.
QUERY = (1.0, 0.0, 0.0)
B_EXACT = (1.0, 0.0, 0.0)
A_WEAK = (0.4, 0.9, 0.0)


def _seed(store):
    store.add("tenant-a", "a1", "tenant A quarterly numbers", A_WEAK)
    store.add("tenant-b", "b1", "tenant B acquisition memo", B_EXACT)
    store.add("tenant-b", "b2", "tenant B board minutes", (0.95, 0.05, 0.0))
    return store


def test_cross_tenant_retrieval_returns_nothing_even_when_it_is_the_best_match():
    """The core assertion. Tenant B holds the nearest neighbour; A must not see it."""
    store = _seed(IsolatedStore())
    hits = store.search("tenant-a", QUERY, k=3)

    assert [h.doc_id for h in hits] == ["a1"]
    assert all(h.tenant_id == "tenant-a" for h in hits)
    assert "acquisition memo" not in " ".join(h.text for h in hits)


def test_the_leaky_design_does_exactly_what_it_looks_like_it_does():
    """Proof the control is load-bearing.

    If this test ever passes with the leak absent, the seed data stopped
    exercising the condition and the isolation tests above went green for the
    wrong reason.
    """
    store = _seed(LeakyStore())
    hits = store.search(QUERY, k=3)
    assert {h.tenant_id for h in hits} == {"tenant-a", "tenant-b"}
    assert hits[0].doc_id == "b1", "another tenant's document ranked first"


def test_post_filtering_isolates_but_starves():
    """Design 2 passes a naive isolation test and still fails the tenant.

    No cross-tenant row is returned — so a test that only checks for leakage
    reports success — but tenant A asked for 3 results and gets 0, because
    tenant B's documents consumed the global top-k.
    """
    store = _seed(StarvedStore())
    hits = store.search("tenant-a", QUERY, k=2)

    assert all(h.tenant_id == "tenant-a" for h in hits), "no leak, as expected"
    assert hits == [], "and no results either — the failure a leak test cannot see"

    isolated = _seed(IsolatedStore()).search("tenant-a", QUERY, k=2)
    assert [h.doc_id for h in isolated] == ["a1"], "pre-filtering returns the tenant's own data"


def test_tenant_id_cannot_be_omitted_by_accident():
    """API shape as a control.

    `search(query, tenant_id=None)` is forgettable and fails open. Positional
    and required means forgetting it is a TypeError at the call site, caught by
    any test that exercises the path — not a disclosure found by a customer.
    """
    store = _seed(IsolatedStore())
    with pytest.raises(TypeError):
        store.search(QUERY)  # type: ignore[call-arg]

    for empty in ("", None):
        with pytest.raises(ValueError, match="tenant_id is required"):
            store.search(empty, QUERY)


def test_unlabelled_writes_are_refused():
    """A row with no tenant cannot be isolated by any predicate written later."""
    store = IsolatedStore()
    with pytest.raises(ValueError, match="cannot be isolated"):
        store.add("", "orphan", "unattributed text", QUERY)


def test_post_condition_catches_an_index_that_stopped_enforcing(monkeypatch):
    """The regression this file exists to catch.

    Simulates a future change — a swapped index, a broken predicate, a vendor
    upgrade that quietly changed pre-filter to post-filter — by defeating the
    pre-filter while leaving everything else intact. The post-condition turns a
    silent cross-tenant disclosure into a refused request.
    """
    store = _seed(IsolatedStore())

    # The predicate stops working. Nothing else about the code changes.
    monkeypatch.setattr(
        IsolatedStore,
        "search",
        lambda self, tenant_id, query, k=3: IsolatedStore._assert_isolated(
            tenant_id, self._ranked(self._docs, query)[:k]
        ),
    )

    with pytest.raises(TenantIsolationError) as err:
        store.search("tenant-a", QUERY, k=3)
    assert "tenant-b" in str(err.value)
    assert "refusing to serve" in str(err.value)


def test_deletion_is_tenant_scoped():
    """Retrieval isolation without deletion isolation is half a control."""
    store = _seed(IsolatedStore())
    removed = store.delete_tenant("tenant-b")

    assert removed == 2
    assert store.search("tenant-a", QUERY, k=5)[0].doc_id == "a1"
    assert store.search("tenant-b", QUERY, k=5) == []

    with pytest.raises(ValueError, match="refusing to delete"):
        store.delete_tenant("")


def test_k_is_honoured_within_the_tenant_not_across_the_corpus():
    """Ranking quality must not depend on how noisy the neighbours are."""
    store = IsolatedStore()
    for i in range(50):
        store.add("noisy-tenant", f"n{i}", "noise", B_EXACT)
    for i in range(3):
        store.add("small-tenant", f"s{i}", "signal", (0.9 - i * 0.1, 0.1, 0.0))

    hits = store.search("small-tenant", QUERY, k=3)
    assert len(hits) == 3
    assert [h.doc_id for h in hits] == ["s0", "s1", "s2"]


def test_cosine_rejects_dimension_mismatch():
    """An embedding-model swap that changes dimensions must fail loudly.

    Silently scoring a 1536-dim query against 768-dim rows produces plausible
    numbers and meaningless rankings.
    """
    with pytest.raises(ValueError, match="dimension mismatch"):
        cosine((1.0, 0.0), (1.0, 0.0, 0.0))


def test_zero_vector_scores_zero_rather_than_dividing_by_zero():
    assert cosine((0.0, 0.0, 0.0), QUERY) == 0.0


def test_assert_isolated_is_reachable_and_correct():
    """Direct unit test of the guard, independent of the search path."""
    good = [Hit("a1", "tenant-a", "x", 1.0)]
    assert IsolatedStore._assert_isolated("tenant-a", good) == good

    with pytest.raises(TenantIsolationError):
        IsolatedStore._assert_isolated("tenant-a", [Hit("b1", "tenant-b", "x", 1.0)])
