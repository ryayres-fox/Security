# AI security

Two controls, both runnable, both with tests written so that removing the control
makes them fail.

| | |
|---|---|
| **[`tenant-isolation/`](tenant-isolation/)** | Multi-tenant isolation in an embedding store — three designs, and the test that tells them apart |
| **[`prompt-injection/`](prompt-injection/)** | A tool-authorization gate, plus a regression corpus that assumes the model is already compromised |

```bash
python -m pytest ai-security -q     # 34 tests
```

---

## The position these encode

Most published AI-security guidance is about **making the model behave**: system
prompts that instruct it to ignore instructions, classifiers over the input,
scoring the output for injection likelihood, red-team prompts that a given model
version resists. All of it is measuring the model.

That is a real activity with real value, and it is not a control. It fails
exactly when it matters — against the payload nobody tested — and it fails
silently, because a compromised model produces confident, well-formatted output.
Worse, every result expires: an evaluation is a measurement of one model version,
and the next upgrade invalidates it without changing a line of your code.

The controls here take the opposite side. **Assume the model is fully compromised
by content it retrieved.** Assume it emits whatever tool call the injected text
asked for. Then ask what still holds. What still holds is deterministic code
between the model and anything that matters:

- Retrieval is scoped by a predicate applied *before* ranking, and re-verified
  after, in code the prompt cannot reach.
- Authorization is computed from session state established at authentication.
  No input to that computation is reachable from the prompt, the documents, or
  the model's output.
- Irreversible actions require a token bound to the exact arguments a human
  approved.

Those survive a model upgrade, because they never depended on the model.

## The review-gate model

The engineering practice around this matters more than either code sample, and
it is the part that does not appear in most portfolios:

**A security determination is a decision, not a comment.** It names the control,
the enforcement point, and the test that proves the control is in place. It is
either met before release or it is explicitly accepted, in writing, with an
owner and an expiry. "I raised a concern in review" is not a determination.

**A release precondition is not a ticket.** A ticket competes for priority with
every other ticket. A precondition blocks the release. The difference is whether
the control ships with the feature or six sprints later.

**A finding belongs in the regression corpus, not the backlog.** A prompt
injection that worked once is a permanent test case. Filed as a ticket it gets
fixed and forgotten, and the next refactor reintroduces it with nobody watching.
Added to [`prompt-injection/corpus.json`](prompt-injection/corpus.json) it fails
the build the day it comes back. Every case in that corpus states which gate rule
must stop it, so a case that starts passing for a *different* reason than it used
to fails the assertion too — because a control that blocks by accident will stop
blocking after the next refactor.

**The distinction between authoring a control and requiring one is worth
keeping.** They are different contributions and both are real. Writing the
migration that adds tenant scoping is engineering. Holding a release until the
migration exists is security. Blurring them costs you the ability to describe
either accurately.

## What these are not

Not a model evaluation harness, not a jailbreak collection, not a guardrail
product. There is no LLM call anywhere in this directory — deliberately. Every
test runs deterministically in under a second and asserts on an authorization
decision or a result set, never on generated text. A test whose expected output
is model-generated is a test that will be quarantined the first time it flakes,
and quarantined tests do not defend anything.

The payloads in the corpus are original, written from the public OWASP Top 10
for LLM Applications (2025) categories. They illustrate a category of attack.
They are not drawn from any product, engagement, or finding.
