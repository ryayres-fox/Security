# Scanning without a commercial platform — why open source, and where it stops

Most teams are not choosing between a great scanner and a bad one. They are stuck
between **nothing** and a **six-figure platform** — Wiz, Tenable, or a
CNAPP-class suite — that their budget or procurement cycle will not reach this
year.

This is what to do in that gap: which open-source tools stand in for the
platform, **why each one earns its seat**, and — said plainly, so nobody is
misled — **what a platform gives you that open source does not.**

> This is not an argument against commercial platforms. When you can afford one,
> the correlation graph and the runtime reach below are worth the money. This is
> about the year before you can, and about not pretending the substitute is
> identical.

The buildable version of everything here is the reference implementation
**"Two Lanes and a Canary"** — an all-open-source scanning estate with an
integrity loop, published as shape, not specifics.

---

## What a commercial platform actually sells you

You are not paying for "scanning." Scanning is free — the tools below are the
same categories the platforms run internally. You are paying for five things,
and it is worth naming them because open source replaces some cleanly and some
not at all.

| What you're buying | What it means |
|---|---|
| **Breadth under one login** | CSPM, workload, identity, vulnerability and dependency scanning in one product, one schema, day one |
| **Correlation — the graph** | The crown jewel: *"this public bucket **+** this over-privileged role **+** this reachable CVE = an attack path."* Not a list of findings — a picture of which findings combine into a way in |
| **Agentless runtime reach** | It sees what is *actually running*, at scale, without you wiring collectors |
| **Maintained intelligence** | Vendor-updated rule and advisory databases, severity, and fix guidance — you don't own the upkeep |
| **Someone to call** | Support, SLAs, a throat to choke at 2 a.m. |

Keep that list in view. It is the honest scorecard for everything that follows.

---

## The open-source estate, mapped to what it replaces

Each surface below has an open-source seat (the tool bench in *Two Lanes and a
Canary*). The last column is the part vendors leave out of the comparison.

| Surface | Platform capability | Open-source seat | How close |
|---|---|---|---|
| **Secrets** | connector scans the repo | `gitleaks` (full history) + `trufflehog` (verifies) | **OSS wins** — history depth + live-credential verification |
| **SAST** | pattern + some dataflow | `semgrep` · `bandit` | Close for pattern classes; platform adds deeper cross-file dataflow |
| **IaC** | config checks | `checkov` · `trivy config` · `terrascan` | **Parity** on misconfiguration rules |
| **Dependencies (SCA)** | vuln DB per ecosystem | `osv-scanner` | **Parity** — one advisory DB, every ecosystem |
| **Containers** | image scanning | `trivy` · `grype` · `hadolint` | **Parity** |
| **SBOM → CVEs** | inventory + match | `syft → grype` | **Parity** — and you own the SBOM as evidence |
| **Kubernetes** | manifest posture | `kubeconform` · `checkov` · `kubescape` | Parity on *config*; not runtime |
| **CSPM** | cloud posture rules | `prowler`-class · `scout`-class | Close on posture; **not the graph** |
| **CIEM / identity graph** | who-can-reach-what | — | **Largely not replicated** |
| **Runtime / workload (CWPP)** | agent sees live behavior | (`falco`-class, separate build) | **Not replicated** by the CI estate |
| **Attack-path correlation** | toxic-combination graph | — | **Not replicated** — you get findings, not paths |

Read the last column top to bottom. The estate reaches **parity or better on
everything that examines a description of the system** — code, config,
dependencies, images, manifests. It does **not** reach the graph, the identity
correlation, or agentless runtime. That boundary is the whole point of this page.

---

## Why each open-source seat earns it (not a poor-man's version)

Several of these are not merely "good enough." They do a specific thing the
bundled equivalent often does *worse*:

- **`gitleaks` — full git history, not the tip.** A secret rotated out of the
  working tree is still in history, and history is where it stays. Many platform
  connectors scan the current tree; this does not.
- **`trufflehog` — verification.** It checks a candidate against the real
  provider. A hit is a *live* credential, not a maybe — which is the difference
  between an alert and an incident.
- **`osv-scanner` — one advisory DB across every ecosystem.** It replaces a
  drawer of per-language scanners with a single source, so "are we exposed to
  CVE-X" has one answer, not six.
- **`syft → grype` — the SBOM is its own evidence.** You keep the bill of
  materials as an artifact, so when the *next* advisory drops you can answer
  "were we ever shipping that" retroactively, without re-scanning history.
- **`kubescape` / render-first Kubernetes.** Score the *rendered* objects, never
  an empty template — the difference between checking what deploys and checking
  nothing.
- **`conftest` / OPA — house rules that are themselves unit-tested.** Your
  policies ship with tests proving they fire. A platform's rules you take on
  faith.
- **`actionlint` / `zizmor` — CI-workflow security.** A vulnerability class most
  estates, and some platforms, never scan at all: the pipeline that runs
  everything else.

The estate keeps a **second opinion on evidence, not on habit** — where two
tools overlap (three IaC scanners), the overlap is *measured* before a seat is
retired. That is [`scanner-strategy.md`](scanner-strategy.md)'s "why run
overlapping tools," and it is only affordable because the
[`findings-normalizer/`](../findings-normalizer/) deduplicates across them.

---

## Where open source genuinely stops — say it out loud

If you deploy this and tell your leadership you now have "what Wiz does," you
will be wrong in four specific ways:

1. **No attack-path graph.** You get a *list* of true findings, not a *picture*
   of which three of them chain into a breach. Correlating them is manual, and
   it is the single largest thing you are not getting.
2. **No agentless runtime at scale.** The CI estate sees descriptions and cloud
   posture. It does not watch live process behavior across a fleet. That is a
   different build (a `falco`-class agent), not a config file.
3. **You own the upkeep.** Rule updates, dedup, severity normalization, tool
   upgrades, the pipeline itself. A platform rents you a team; here **you are the
   team.**
4. **No support and no SLA.** When a scanner breaks at 2 a.m., the vendor is you.

> The honest trade: a platform sells you **correlation and someone to call.**
> Open source sells you **every layer**, and the bill arrives as **your time.**

---

## The one thing the open-source estate has that platforms often don't

A commercial dashboard glows green too. **"The scanner ran" and "the scanner was
looking" are different claims** — and that gap lives inside expensive platforms
as readily as inside a shell script. A scanner that loaded zero rules reports a
clean scan in either one.

The estate's answer is the **integrity loop** — a canary that asserts detection
(does the scanner flag a planted defect?), a coverage floor that pins the
denominator, and a run-over-run delta that forces a *named cause* onto every
count move. Clean results are not evidence until they clear it. It costs seconds
per run, it is free, and it is the **part worth building first**.

This is where a careful open-source estate can actually *beat* a platform you are
not auditing: you can prove your controls ran. See
[`silent-failure-patterns.md`](silent-failure-patterns.md) for the failures that
loop exists to catch, and the *Two Lanes and a Canary* reference implementation
for the loop drawn out.

---

## If you're standing this up with no budget

The starting order is in [`scanner-strategy.md`](scanner-strategy.md#deciding-what-to-run)
— secrets first, then IaC, then one tuned SAST, then dependency/container, then
posture. Two additions specific to doing it without a platform:

- **Build the canary before the coverage.** The first scanner you add is worth
  nothing until you can prove it was looking. The integrity loop is cheaper to
  add on day one than to retrofit onto a year of green checkmarks.
- **Write the second lane early.** One zero-argument script that runs the same
  tools locally and drops a dated evidence directory is your compensating control
  for the day CI is down — *"when lane 1 is down, lane 2 is the record, not a
  gap."*

The whole thing is buildable by a small team in about a week. What you will not
have is the graph and the runtime reach — so **name that gap in your risk
register** rather than letting a green dashboard imply it is covered. A gap named
is a gap; a gap unnamed is a lie.

---

## Bottom line

A commercial platform is worth it when you can afford it: the attack-path graph
and agentless runtime are real capabilities that open source does not match.
Until then, an open-source estate is **not** a downgrade in the thing that
matters most — knowing your controls actually ran. It is a downgrade in
**correlation and convenience**, and an upgrade in **how much you understand your
own pipeline.**

**Scanners raise the floor. A platform raises it faster. Neither raises the
ceiling** — that is still threat modelling and human review
([`threat-model.md`](threat-model.md), [`review-standard.md`](review-standard.md)).
