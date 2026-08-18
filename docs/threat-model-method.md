# Threat modelling as a communication tool

A method for writing threat models that people outside security actually read, act on, and fund.
[`threat-model.md`](threat-model.md) is the worked example. This is the reusable version — take it,
change it, use it.

---

## The problem this solves

Most threat models are correct and useless.

They are correct because STRIDE is a good taxonomy and the person who wrote it knew what they were
doing. They are useless because the audience that has to *act* — the engineering manager who
allocates the sprint, the director who signs the risk acceptance, the exec who decides whether to
ship — cannot extract a decision from them.

Here is a real row from a real threat model, lightly disguised:

> | Threat | STRIDE | Severity | Mitigation |
> |---|---|---|---|
> | Attacker performs IDOR on the retrieval endpoint | Information Disclosure | High | Authorization checks in the service layer |

Everything in that row is true. Now watch it fail at its job:

- A manager cannot tell what "High" costs. High compared to what? High like a fine, or high like a
  weekend?
- "Authorization checks in the service layer" — are they *on*? Were they on last Tuesday? The row
  cannot distinguish a working control from an intention.
- There is no decision in it. Nobody knows what they are being asked for.

So it gets acknowledged and filed. The security team concludes the business does not care about
security. The business concludes security produces documents nobody can use. Both are wrong, and the
document caused it.

---

## Five changes that fix it

### 1. Lead with the consequence, not the mechanism

The mechanism is *how*. The consequence is *what it costs*. Only one of those is decision-relevant
to a non-specialist, and it is not the one security people naturally write first.

| Instead of | Write |
| --- | --- |
| "IDOR in the retrieval path" | "One customer reads another customer's documents" |
| "Prompt injection via retrieved context" | "Content a customer uploads causes the system to act against them" |
| "Insufficient audit log integrity controls" | "An attacker edits the record of what they did" |

Keep the mechanism. Move it down. A reviewer who wants it will find it; a manager who does not need
it is no longer blocked by it.

### 2. Write the headline

For each threat, write the sentence you would have to say publicly if it happened. A customer
notification, a status page, a journalist's question.

> *"A customer was able to retrieve documents belonging to another customer. We cannot determine how
> many were viewed."*

This does more work than any severity scale:

- **It is self-prioritising.** Put the headlines side by side and the order is obvious to everyone in
  the room, with no argument about whether something is a 7.5 or an 8.1.
- **It exposes threats that are not real.** If you cannot write a headline that would alarm anyone,
  you may be modelling a finding rather than a threat.
- **It transfers instantly.** Nobody needs the CVSS vector explained.
- **It is uncomfortable to write**, which is the point. Discomfort is the signal you have found the
  actual consequence rather than a technical restatement.

The second sentence — *"we cannot determine how many"* — is often worse than the first. Not knowing
the scope is frequently more expensive than the breach, because it forces you to assume the maximum.

### 3. Separate "we have a control" from "the control is running"

This is the change that matters most, and almost no threat model makes it.

A mitigation column says a control exists. It cannot say whether it works *now*. Those diverge
silently and constantly:

- a policy set that registers zero checks while the scan reports success
- a scanner pinned to a version that does not exist, failing at startup for weeks
- an ignore rule on a path the risk does not actually travel

Each of those was found in this repository's own code. In every case the control was documented,
reviewed, and doing nothing — see [`silent-failure-patterns.md`](silent-failure-patterns.md).

So use two columns, or one column with two states:

| | Meaning |
| --- | --- |
| ✅ **Verified** | A test or gate proves it. Name it. It runs in CI |
| ⚠️ **Partly** | Present, with a stated gap |
| ❌ **Asserted** | We believe it is on. Nobody has checked |

An honest ❌ is worth more than a dishonest ✅. It converts an invisible risk into a visible one,
which is the only kind anyone can fund.

**The test for a ✅:** could this control have failed without anyone noticing? If the answer is yes,
it is not verified — it is asserted with confidence.

### 4. End every row in a decision state

A threat model is not a report. It is a request. Every row resolves to one of:

**Mitigated** · **Accepted** (owner + date) · **Needs a decision** · **Out of scope**

Then pull the *needs a decision* rows into their own section, with options and costs:

| Option | Cost | Residual |
| --- | --- | --- |
| Enable on publication | £0 | Gap persists until then. **Recommended** |
| Purchase the licence | Per-committer | Closed now |
| Accept as-is | £0 | Detection only, indefinitely |

Name who decides and by when. A recommendation is not pressure — it is you doing your job. Reviewers
who present options without one are outsourcing the judgement they were hired for.

### 5. Say what you are not covering

A document that lists only threats reads as a complete inventory, and gets treated as a clean bill of
health for everything absent from it.

An explicit out-of-scope table costs four lines and prevents the most damaging misreading available:
*"security looked at this and it was fine."*

---

## The shape

```markdown
# Threat model — <system>

**Scope:** … **Method:** … **Last reviewed:** … **Owner:** …

## How to read this if you are not a security engineer
   Which columns are for them. What decision is being asked for.

## What we are protecting
   Ranked by cost of loss. A "worst realistic day" column.

## Trust boundaries
   A diagram, and the ASSUMPTION being made at each line.

## The threats
   Per threat: what an attacker gets · the headline · how ·
   control · enforced? · residual · status. STRIDE last.

## Decisions required
   Options, costs, residual, recommendation, who decides, by when.

## Out of scope, deliberately

## How this document stays true
```

---

## Practical notes

**Model trust boundaries, not components.** A boundary is where the trust level changes, and it is
where an assumption gets made. Listing every microservice produces a long document and finds
nothing; naming five boundaries and interrogating the assumption at each finds most of what matters.

**Say the assumption out loud.** "The caller is who they claim to be." "The query is scoped to the
caller's tenant." "The model's output is a request, not a decision." Written down, wrong assumptions
become obvious to people who are not security specialists — which is exactly the audience most
likely to know the assumption is false.

**Rank by cost of loss, not by CVSS.** They disagree more often than is comfortable. A medium-severity
cross-tenant leak can end a contract; a critical-severity issue in a component nobody reaches may
not be worth this quarter.

**Keep it short enough to be read.** Eight threats that get read beat forty that get filed. Rank
ruthlessly, cut the tail, and put the survivors first.

**Re-review on boundary changes, not on a calendar.** A new ingress, a new data store, a new tool an
agent can call. A quarterly review of an unchanged system is theatre; an unreviewed new boundary is
how threats get missed.

**Write it with the engineers, not for them.** The threats a team already suspects are usually the
real ones, and a model produced in a room is adopted. One delivered as a finished artifact is
received.

---

## Adopting this

Take the shape above and change what does not fit. Specifically:

- **Currency and cost model** — the examples use £; the point is that options carry costs at all
- **The verification column** is worth keeping even without CI to point at. "Asserted" is still
  useful information, and writing it down is what eventually funds the check
- **Severity scales** — if yours is mandated, keep it *and* add the headline. They coexist; the
  headline is what gets the room to agree on the scale's output
- **STRIDE** is one taxonomy. LINDDUN for privacy, or a kill-chain framing, slot into the same shape

The only part that does not survive removal is **separating verified from asserted**. Everything else
is presentation. That one is the difference between a threat model that describes a system and one
that describes reality.
