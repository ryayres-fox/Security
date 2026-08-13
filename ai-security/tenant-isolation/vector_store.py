"""Multi-tenant isolation for an embedding store.

The control is one line of predicate. Everything interesting is about *where*
that predicate lives and what happens when someone forgets it.

Three designs, in the order teams usually arrive at them:

1. `LeakyStore` — the store searches globally and returns neighbours; the caller
   filters. This is the shape you get when a vector index is added to an
   existing service as a library. It is not a bug in the store, and every
   individual line of it is defensible, which is exactly why it survives review.
   It leaks the first time any caller forgets, and callers multiply.

2. `StarvedStore` — the store filters, but *after* computing global top-k. No
   cross-tenant data is returned, so it passes an isolation test. It fails a
   different way: a large tenant's documents crowd the global top-k and a small
   tenant gets fewer results than it asked for, or none. This one is worse than
   a leak in one specific respect — it looks correct in the security test and
   degrades silently in production.

3. `IsolatedStore` — the tenant is a required argument, the predicate is applied
   before ranking, and a post-condition re-checks every returned row against the
   requested tenant. The post-condition is not redundant: it is what converts a
   future refactor of the index from a silent leak into a loud failure.

The reference implementation is deliberately naive about vectors — exact cosine
over a Python list. A real deployment uses pgvector or a managed index, where
the isolation question becomes "does the ANN index enforce the predicate before
traversal, or does the engine post-filter?" That is a question to ask a vendor
in writing, and the answer is frequently the second one.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


class TenantIsolationError(RuntimeError):
    """Raised when a result set contains a row from another tenant.

    This should be unreachable. If it is ever raised, an isolation control has
    already failed and the request must not be served.
    """


@dataclass(frozen=True)
class Document:
    doc_id: str
    tenant_id: str
    text: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class Hit:
    doc_id: str
    tenant_id: str
    text: str
    score: float


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class _BaseStore:
    def __init__(self) -> None:
        self._docs: list[Document] = []

    def add(self, tenant_id: str, doc_id: str, text: str, embedding: tuple[float, ...]) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required on write; an unlabelled row cannot be isolated")
        self._docs.append(Document(doc_id, tenant_id, text, tuple(embedding)))

    def _ranked(self, docs: list[Document], query: tuple[float, ...]) -> list[Hit]:
        scored = [
            Hit(d.doc_id, d.tenant_id, d.text, cosine(query, d.embedding)) for d in docs
        ]
        return sorted(scored, key=lambda h: (-h.score, h.doc_id))


class LeakyStore(_BaseStore):
    """Design 1. Isolation is the caller's job, which means it is nobody's job."""

    def search(self, query: tuple[float, ...], k: int = 3) -> list[Hit]:
        return self._ranked(self._docs, query)[:k]


class StarvedStore(_BaseStore):
    """Design 2. Filters after ranking. Isolated, and quietly lossy."""

    def search(self, tenant_id: str, query: tuple[float, ...], k: int = 3) -> list[Hit]:
        global_top_k = self._ranked(self._docs, query)[:k]
        return [h for h in global_top_k if h.tenant_id == tenant_id]


class IsolatedStore(_BaseStore):
    """Design 3. Pre-filter, then rank, then verify.

    `tenant_id` is positional and required. That is a deliberate API choice: an
    optional `tenant_id=None` filter is forgettable, and the failure mode of
    forgetting it is a cross-tenant disclosure rather than an exception.
    """

    def search(self, tenant_id: str, query: tuple[float, ...], k: int = 3) -> list[Hit]:
        if not tenant_id:
            raise ValueError("tenant_id is required; refusing to search across all tenants")

        # Predicate before ranking: top-k is computed within the tenant, so one
        # tenant's document volume cannot displace another's results.
        scoped = [d for d in self._docs if d.tenant_id == tenant_id]
        hits = self._ranked(scoped, query)[:k]

        # Post-condition. Unreachable in this implementation by construction —
        # which is the point. It exists so that a future change to the index,
        # the predicate, or the storage engine fails loudly here instead of
        # succeeding quietly in a response body.
        return self._assert_isolated(tenant_id, hits)

    @staticmethod
    def _assert_isolated(tenant_id: str, hits: list[Hit]) -> list[Hit]:
        foreign = {h.tenant_id for h in hits if h.tenant_id != tenant_id}
        if foreign:
            raise TenantIsolationError(
                f"result set for tenant {tenant_id!r} contained rows from {sorted(foreign)!r}; "
                "refusing to serve"
            )
        return hits

    def delete_tenant(self, tenant_id: str) -> int:
        """Deletion is tenant-scoped too.

        Retrieval isolation without deletion isolation is half a control: it
        holds for reads and fails the first time a tenant exercises a deletion
        right and takes someone else's rows with it.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required; refusing to delete across all tenants")
        before = len(self._docs)
        self._docs = [d for d in self._docs if d.tenant_id != tenant_id]
        return before - len(self._docs)
