# Tenant isolation in an embedding store

The control is one predicate. Everything that matters is *where* it lives and
what happens when someone forgets it.

```bash
python -m pytest ai-security/tenant-isolation -q     # 11 tests
```

## Three designs

| | Leaks? | Passes a naive isolation test? | Actually correct? |
|---|---|---|---|
| **`LeakyStore`** — store ranks globally, caller filters | **Yes** | No | No |
| **`StarvedStore`** — store ranks globally, then filters | No | **Yes** | **No** |
| **`IsolatedStore`** — predicate before ranking, verified after | No | Yes | Yes |

`StarvedStore` is the interesting one. It returns no cross-tenant rows, so an
isolation test reports success — and a small tenant still gets zero results,
because a large tenant's documents consumed the global top-k before the filter
ran. It is correct on the axis being tested and broken on the axis nobody
thought to test. [`test_post_filtering_isolates_but_starves`](test_tenant_isolation.py)
is the assertion that separates them.

## Three design decisions

**`tenant_id` is positional and required.** An optional `tenant_id=None` filter
is forgettable, and the failure mode of forgetting it is a cross-tenant
disclosure. Required and positional means forgetting it is a `TypeError` at the
call site, caught by any test that exercises the path.

**The post-condition re-checks every returned row.** It is unreachable in this
implementation, by construction — which is the point. It exists so that a future
change to the index, the predicate, or the storage engine fails loudly instead of
succeeding quietly into a response body.
[`test_post_condition_catches_an_index_that_stopped_enforcing`](test_tenant_isolation.py)
simulates exactly that, by defeating the pre-filter and leaving everything else
intact.

**Deletion is scoped too.** Retrieval isolation without deletion isolation is
half a control: it holds for reads and fails the first time a tenant exercises a
deletion right and takes someone else's rows with it.

## Carrying this to a real index

The reference implementation is exact cosine over a Python list — deliberately
naive, so the isolation logic is the only thing to read. In a real deployment on
pgvector or a managed vector service, the same question becomes:

> Does the ANN index apply the tenant predicate **before** graph traversal, or
> does the engine retrieve globally and post-filter?

Post-filtering is `StarvedStore`, and it is a common default. Ask the vendor in
writing, and test it with a lopsided corpus — one tenant with thousands of near-
duplicate rows, another with three — because a balanced test dataset cannot
distinguish the two designs at all.

Row-level security in PostgreSQL is a stronger answer than an application
predicate, because it moves enforcement below the ORM where a forgotten `WHERE`
clause cannot bypass it. The application-layer version here is what you build
when the store does not offer that.
