# Writing detections that prove they fire

A detection nobody validated is a scanner that loaded zero rules: it reports
"monitoring" and enforces nothing. This is the discipline that makes a detection
a **control** rather than a saved search — a fixed output schema, a risk score,
suppression that doesn't blind you, and a **validation gate** that fails a
malformed detection *before* it ships instead of during an incident.

Written from years of practice on Splunk, but the shape is platform-agnostic —
the same applies to Sentinel, Elastic, Panther, or a Sigma rule set.

---

## 1 · Every detection emits the same shape

The first discipline: a detection is not free-form query output that dumps
whatever fields it happened to have. It emits a **fixed schema**, so everything
downstream — triage, ticketing, scoring, suppression — can rely on it.

- **Identifiers** (at least one, *extracted from the event*): a user
  (`user` / `src_user` / `dest_user`), an IP (`src_ip` / `dest_ip`), or a host
  (`src_host` / `dest_host`). Pull them from the log — **an identifier you
  calculated from a lookup is an identifier you can be silently wrong about.**
- **Metadata:** `alert_time` (when the event happened) *and* the run time (when
  the search fired) — you need both; a friendly name; type (alert vs stats);
  severity; score; the data source; the suppression/whitelist list name; and the
  **remediation** — what the analyst actually does.
- **IOCs** where relevant: hash, URL, filename, domain.
- **Hygiene:** lowercase every field, use one approved field-name list, and strip
  working/comment fields from the final output.

Why the schema is the control, not paperwork: if there is no field for the
identifier, the remediation, or a false-positive marker, **you cannot act on it
or report on it later — no matter how good the query is.** That is a schema
decision, not a reporting decision (the same point the
[findings normalizer](../findings-normalizer/) makes about its own store).

## 2 · Score by severity **and** frequency

Severity alone over-alerts. Multiply two axes:

| Severity | | Frequency (how normal the behaviour is) | |
|---|---|---|---|
| info | 0 | frequent | 1 |
| low | 2 | regular | 2 |
| medium | 3 | rare | 3 |
| high | 4 | never | 4 |
| critical | 5 | | |

**score = severity × frequency.** A high-severity thing that happens all day
(frequency 1) scores *below* a medium thing that should never happen at all
(frequency 4). You triage the **product**, not the label — the same logic as
pairing [CVSS with EPSS](scanner-strategy.md): how bad × how likely, not how bad
alone.

## 3 · Suppress without going blind

Alert fatigue kills a program — analysts stop reading a channel that cries wolf.
Suppress a **known, acknowledged case** for a window (e.g. 24h) by checking a
summary index for a prior fire of the *same* detection on the *same* subject.

The rule that keeps it safe: **suppress the case, never the detection.** A
detection that is globally muted is a detection that is off — and an off
detection that still shows "enabled" is exactly the silent-failure this
repository is about.

## 4 · The validation gate — the part worth stealing

This is the detection-engineering equivalent of the repo's
[canary](without-a-commercial-platform.md): a detection that does not conform to
the schema **fails before it ships**, rather than quietly emitting an
unactionable alert in the middle of an incident.

Run every new detection's output through a validation search that asserts, field
by field, PASS / FAIL / "not present":

- **Identifier present?** `coalesce(user, src_user, dest_user, src_ip, src_host)`
  → FAIL if none. A detection with no subject is a page with no phone number.
- **Required metadata present?** `alert_time`, friendly name, source, remediation
  → FAIL if null.
- **Half-identifiers?** an IP with no resolved host is a FAIL — resolve it or
  drop it.
- **Enumerations valid?** severity is one of the allowed values; frequency is
  one of the allowed values; `score >= 0`; type is `alert`.
- **Hygiene?** working/comment fields stripped.

Any FAIL and the detection does not go live. The point is the one this whole
repository keeps making:

> **"The detection ran" and "the detection was well-formed enough to act on" are
> different claims.** A detection that fires with no identifier or no remediation
> produces an alert nobody can action — which, in an incident, is the same as no
> alert. The validation gate makes conformance a *checked fact*, not a hope.

## The pre-ship checklist

- [ ] At least one identifier, **extracted from the log**
- [ ] All required metadata fields present
- [ ] `severity × frequency` score computed
- [ ] Suppression scoped to the **case**, not the detection
- [ ] Remediation written — what the analyst does, in one line
- [ ] Passes the validation search — **zero FAILs**
- [ ] **Test-run before enabling.** A detection enabled untested is a detection
  you will debug during the incident it was supposed to catch.

---

*A detection is a control, and this repository's whole argument is that a control
is not real until you can prove it ran and was looking. The validation gate is
how you prove a detection was looking. See also
[`silent-failure-patterns.md`](silent-failure-patterns.md) and, for the home-lab
side of detection, [`../homelab/detection-engineering.md`](../homelab/detection-engineering.md).*
