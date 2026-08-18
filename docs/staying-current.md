# Staying current — an automated briefing habit

A security picture decays. The controls you shipped last quarter defend against
last quarter's threat model, and the gap is invisible until something in the wild
walks through it. **Currency is a control** — and like any control, it is better
automated than left to willpower.

The practice here is two automated briefings a day, built from public RSS/Atom
feeds: a **morning** preview (forward-looking, start-of-day) and an **evening**
recap (what actually happened). Each is a fetch-summarise-dedupe pass over a
curated feed set, and the whole thing is buildable by anyone in an afternoon.

---

## Why this lives in a security portfolio

This is not "I read the news." The threat-intel feeds surface **CVEs, CISA
advisories, and active exploitation** — the same signals that should drive scan
prioritisation and remediation SLAs. Your scanners tell you what is vulnerable in
*your* code; the briefing tells you what is being exploited *in the wild*. You
need both, and reading the second one a day late is the difference between
patching ahead of a campaign and doing incident response after it.

- A newly **actively-exploited CVE** in your stack is not a headline — it is an
  unplanned item on today's remediation queue. See
  [`operating-the-scan-flow.md`](operating-the-scan-flow.md) and
  [`scanner-strategy.md`](scanner-strategy.md) for where it lands (RA-5 is
  monitoring *and* scanning; the news is the monitoring half).
- World and AI context move the ground under the controls: geopolitics drives
  campaign timing, and AI-agent risks are a live and fast-moving attack surface.
- A stale threat model is a [silent-failure pattern](silent-failure-patterns.md)
  of its own — it reports "covered" long after it stopped being true.

---

## The feed set (public, and deliberately cross-spectrum)

Three groups. Everything here is a public feed; the full personal subscription
list is kept as an **OPML** file (the portable feed-export format every reader
and script can import), so the set travels rather than living in one app.

### World news — spanning left, center, and right *on purpose*

| Feed | Lean |
| --- | --- |
| `feeds.bbci.co.uk/news/world/rss.xml` | BBC — center |
| `rss.cnn.com/rss/edition_world.rss` | CNN — center-left |
| `feeds.npr.org/1004/rss.xml` | NPR World — center-left |
| `cbsnews.com/latest/rss/world` | CBS — center-left |
| `abcnews.com/abcnews/internationalheadlines` | ABC — center |
| `moxie.foxnews.com/google-publisher/world.xml` | Fox News — right-leaning |
| `rss.csmonitor.com/feeds/world` | Christian Science Monitor — center |
| `rss.sciam.com/ScientificAmerican-Global` | Scientific American — science |

The spread is the point — see the method below.

### AI

| Feed |
| --- |
| `venturebeat.com/category/ai/feed/` |
| `deepmind.google/blog/rss.xml` |
| `thegradient.pub/feed/` |

### Cybersecurity / threat intel

| Feed | Reliably surfaces |
| --- | --- |
| `bleepingcomputer.com/feed/` | CVEs, CISA "now exploited" advisories, breaches |
| `darkreading.com/rss.xml` | campaigns, threat-actor tradecraft, AI-agent risk |
| `krebsonsecurity.com/feed/` | deep-dive investigations |
| `feeds.feedburner.com/TheHackersNews` | fast CVE / exploit / patch coverage |

---

## The anti-bias method — the part worth stealing

The world feeds span left, center, and right by design, and the method turns that
spread into signal instead of noise:

- **Cross-spectrum agreement is the strongest signal.** When the *same* story is
  reported across left, center, and right, lead with it and group it into one
  entry citing the multiple sources. Consensus across outlets that agree on little
  else is the closest thing to ground truth a news scan produces.
- **Name the divergence, don't inherit it.** Where outlets frame the same event
  differently, say so in a brief neutral aside ("framing differs across outlets")
  — then describe the event factually. Never adopt a single source's slant.
- **This is the repository's own evidence ethos.** Agreement across *independent*
  sources is signal — the same reason the
  [findings normalizer](../findings-normalizer/) records every tool that reported
  a finding rather than collapsing to one. Two independent observers agreeing is
  stronger evidence than one observer asserting.

---

## How it's built

- **Fetch each feed's XML** and pull items from a rolling window — a morning
  preview looks back ~18h, an evening recap ~12h.
- **One bad feed never stops the briefing.** If a feed fails, is empty, or returns
  unreadable/binary content, skip it *silently*. (Feeds go down; the briefing
  still ships. Silent-skip here is the honest kind — the output is a briefing, not
  a coverage claim, so a missing outlet is not a false green.)
- **Large bodies:** save to a temp file and `grep` for `<title>` / `<pubDate>` to
  pull recent headlines rather than parsing the whole document.
- **Dedupe consensus stories** across outlets into a single entry before writing.
- **Output** is scannable: a one-line overview, then World / AI / Security
  sections — short lines, sources cited, CVEs and CISA advisories flagged
  prominently.

## Reading it as a security input, not a news habit

The value is in what you *do* with the security section. A briefing that flags an
actively-exploited CVE and then goes in a drawer is a
[shelf, not a control](operating-the-scan-flow.md). Wire it the other way: the
morning's exploited-in-the-wild items become **inputs to triage** — checked
against your own inventory, and escalated ahead of the backlog if they land in
your stack.

**Currency is cheap to automate and expensive to lack.** The feeds are free, the
fetch is an afternoon of scripting, and the payoff is knowing about the campaign
before it knows about you.
