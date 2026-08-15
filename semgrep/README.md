# Custom SAST rules

Six Semgrep rules, and — as with [`../policies/`](../policies/) — the tests that
prove they run.

```bash
pip install semgrep pytest
pytest semgrep -q          # 16 tests
```

## The rules

| ID | Catches | Why no off-the-shelf rule covers it |
|---|---|---|
| `reference-missing-route-authorization` | A route handler with no guard | Per-route enforcement means an omitted decorator is an open endpoint, not a default-deny. Generic rules cannot know which router is guarded globally |
| `reference-actor-field-from-request-body` | `created_by` / `owner` taken from the request | Attribution spoofing. The field should not be writable at all, and no generic rule knows which of your fields are actors |
| `reference-tenant-scope-from-request` | Tenant identity read from a header or body | The one that ends a contract. Tenancy is application-specific by definition |
| `reference-unscoped-tenant-query` | A query on a tenant-scoped table with no predicate | The case the store's own API boundary cannot see |
| `reference-disabled-tls-verification` | `verify=False` | Converts an encrypted channel into an obfuscated one — still HTTPS in every log, which is why it survives |
| `reference-unsafe-deserialization` | `yaml.load`, `pickle.loads` | Code execution wearing the costume of parsing |

Each carries its NIST 800-53 control IDs in `metadata`, which the findings
normalizer reads straight through.

## Why the tests matter more than the rules

A rule set fails in two directions, and **only one of them is visible**:

1. **It never loads.** A `--config` path resolving to nothing, a YAML error
   swallowed by a wrapper, a rules directory that moved. Semgrep scans, reports
   findings from whatever *did* load, and exits 0.
2. **It loads and never matches.** A pattern that was correct against the code
   as written, and silently stopped after a refactor — a decorator renamed, a
   framework upgraded, `requests` swapped for `httpx`. Present, registered,
   inert.

Both produce the same output as a clean scan: no findings. So both are asserted.

There is a meta-test that demonstrates the problem rather than describing it —
it points Semgrep at an empty rule set and confirms it **exits 0 with no
findings**, identical in every observable way to a clean run with the real rules.

Try it:

```bash
# make one rule inert without breaking its syntax
sed -i '' 's/verify=False/verify=NEVERMATCHES/' semgrep/rules/crypto-and-transport.yml
pytest semgrep -q
# 1 failed — reference-disabled-tls-verification matched nothing
```

## The third assertion

The rules must also **not** fire on `fixtures/compliant/`. Almost no rule set
tests this, and it is what stops one being abandoned: a rule that flags correct
code gets suppressed within a week, and a suppressed rule reports success
forever after.

It earned its place immediately. `reference-tenant-scope-from-request` was
written as a bare `$BODY.tenant_id`, which also matched
`request.state.auth.tenant_id` — **the correct way to obtain a tenant**. The
compliant fixture caught the rule flagging the right answer as loudly as the
wrong one, and the pattern was narrowed with the exclusions written in.

## Adding a rule

1. Write it in `rules/*.yml`.
2. Add a violating function to `fixtures/noncompliant/app.py` and a compliant
   twin to `fixtures/compliant/app.py`.
3. `pytest semgrep -q`. The parametrized tests pick the new ID up from the rule
   source automatically — there is no list to update, which is deliberate: a
   hardcoded list keeps passing when a rule is added and fails to load.
