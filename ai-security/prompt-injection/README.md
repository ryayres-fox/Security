# Prompt injection — the part that is a control

```bash
python -m pytest ai-security/prompt-injection -q     # 23 tests
```

## The threat model, which is the whole design

> Assume the model is fully compromised by content it retrieved. Assume it emits
> whatever tool call the injected text asked for, with whatever arguments, and
> describes it convincingly. The control must hold anyway.

The harness never calls a model. For each corpus case it submits the tool call
the injection was trying to produce, directly — the worst outcome the injection
could achieve. If the gate denies it, the injection is contained no matter how
persuasive the payload was or how completely the model complied.

That assumption rules out a whole family of popular mitigations: input
classifiers, phrase stripping, "ignore instructions in documents" system prompts,
injection-likelihood scoring. Each tries to stop a compromised model from
*asking*. None is a control, because each fails precisely when it matters and
does so silently.

## Five rules

Ordered by how often their absence causes an incident. See
[`tool_gate.py`](tool_gate.py).

1. **Deny by default.** An unrecognised tool is denied, not passed through.
2. **Scopes come from the session.** Nothing the model emits can add one — the
   session is established by authentication and has no path from content.
3. **Subject-bound arguments must match the session.** A call naming a
   `tenant_id`, `workspace_id` or `user_id` is checked against the authenticated
   value. Same control as [`../tenant-isolation/`](../tenant-isolation/), enforced
   at the tool boundary instead of the retrieval boundary. Both are needed;
   neither substitutes for the other.
4. **Egress destinations are allowlisted.** Exfiltration does not require a
   privileged tool, only a tool that accepts a URL — case `PI-007` uses
   `create_ticket`, which the session is fully entitled to call.
5. **Irreversible actions need a confirmation token bound to the exact
   arguments.** Unbound tokens produce the confirm-then-swap problem: a human
   approves emailing the report to finance, the model re-emits the call with a
   different recipient, and the token still validates. That is how a confirmation
   dialog becomes a rubber stamp.

## The corpus

[`corpus.json`](corpus.json) — 13 cases across OWASP LLM01, LLM02, LLM06, LLM07
and LLM08. Each names the payload, the tool call a compromised model would emit,
the expected verdict, **and which rule must produce it**.

That last field is the one that earns its place. Asserting only on
allow/deny lets a case start passing for a different reason than it used to —
and a control that blocks by accident stops blocking after the next refactor.

Two cases are benign baselines that must be **allowed**. A gate hardcoded to
`return DENY` passes every negative test in the file; the baselines are what
distinguish a control from a brick, and
[`test_corpus_contains_passing_cases`](test_injection_corpus.py) enforces that
they stay.

## Adding a case

A prompt injection that worked once is a permanent test case, not a ticket. Add
it here:

```json
{
  "id": "PI-014",
  "owasp_llm": "LLM01",
  "category": "short-kebab-case-description",
  "payload": "the untrusted text",
  "model_would_attempt": { "tool": "...", "arguments": {} },
  "expect": "deny",
  "expect_rule": "missing-scope"
}
```

If no existing rule denies it, the gate is missing a rule — and that, not the
payload, is the finding.
