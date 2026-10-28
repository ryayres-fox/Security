# Lab journal

A dated record of building and testing a virtual security lab on one Mac
(Apple silicon, VirtualBox). It has four parts:

- a gateway that routes, filters and logs every lab packet
- a Kali workstation behind the gateway
- a [Malcolm](https://github.com/cisagov/Malcolm) sensor that receives a
  mirror of all lab traffic
- targets on their own segments. The first one is a retrieval-augmented
  generation (RAG) app with a tenant boundary to attack.

Each entry covers what I set out to do and what happened. It also covers
what broke, how I could tell, the evidence, and what comes next. Failures
stay in. A lab journal that only records what worked is a brochure.

## Why it is written this way

- **For anyone following along.** The commands are the literal ones, each
  with the result it should give. The addresses shown are documentation
  addresses (RFC 5737) standing in for the lab's own plan, host numbers
  preserved: `192.0.2.0/24` for the lab segments, `198.51.100.0/24` for
  the management network. Commands meant to be run use `$TARGET2` and
  `$KEY`. None of the lab can be reached from anywhere else.
- **Tests, with what to read in the output.** Malcolm and the RAG app
  start as initial deployments with light configuration, and each piece
  of configuration is tested as it goes in. Every test gives the command
  or the search, the output it should produce, and the few fields in that
  output that answer the question. A security record has dozens of fields,
  and knowing which ones to read is most of the work.
- **As a continuing-education record.** Each entry carries the date, the
  time spent, the CISSP domains it exercises, and a short summary of what
  I learned. An ISC2 CPE claim asks for supporting documentation and a
  summary of the learning, and the entries are both.
- **From public sources, against synthetic targets.** Everything is written
  from public documentation and the tools' own source code. Nothing here
  comes from an employer's environment.

## The lab

```text
              Internet (the Mac's connection, VirtualBox NAT)
                                 │
                       gateway (Debian 13, arm64)
              nftables: default drop, every new flow logged
              tc mirred: every lab interface copied to "mirror"
       ┌────────────┬────────────┬────────────┬─────────────┐
    seg-kali      seg-t1       seg-t2       mirror        mgmt (host-only)
    kali .10      target-1     target-2     sensor:       Mac .1  gateway .2
                  .18          .22 (RAG)    span NIC,     kali .10
                                            no address    sensor .5 (Malcolm)
```

Each lab host shares a /30 with the gateway and nothing else. Traffic
between any two lab machines is therefore routed. It passes the
gateway's firewall, leaves a log line, and is mirrored to the sensor. On a
single shared segment the same traffic would be switched by the hypervisor,
and no router or sensor would see it.

The sensor has no address on the lab side. Its capture NIC sits on the
mirror network with no address, and its dashboards are on the management
network, which the lab cannot route to.

## Entries

Grouped by milestone. A milestone closes with one entry, written when its
goal is proven. The first two milestones were written up daily, before the
journal moved to one entry per milestone.

### Milestone 1: Kali behind the gateway

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-12 | [Kali is behind the gateway, checked from inside Kali](2026-10-12-behind-the-gateway.md) | 4, 7, 6 | 0.5 h |

### Milestone 2: one clock for the lab

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-13 | [The gateway was thirteen hours behind, and every clock I could read from outside it said it was fine](2026-10-13-gateway-clock-dns.md) | 4, 7, 6, 3 | 1.5 h |
| 2026-10-13 | [The sensor was capturing, and its clock was twelve hours behind](2026-10-13-sensor-clock.md) | 7, 4, 6, 3 | 1.5 h |
| 2026-10-13 | [Proving the sensor's clock comes back, and the package that stopped it](2026-10-13-sensor-clock-proven.md) | 7, 6, 3 | 1.5 h |

### Milestone 3: the RAG baseline, monitored

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-13 | [The RAG baseline, counted three times](2026-10-13-rag-baseline-counted.md) | 6, 7, 4 | 0.5 h |
| 2026-10-13 to 14 | [The baseline counted four times, every box starting itself, and the night the Mac slept](2026-10-14-milestone-3-baseline-monitored.md) | 7, 6, 3 | 2.0 h |

The first two 2026-10-13 entries shared one morning, 09:15 to 12:45 CDT,
and split its time between them: 3.0 h, counted once. The afternoon adds
2.0 h, and Milestone 3's close-out adds 1.0 h that evening, for 6.0 h on
13 October. The close-out's other 1.0 h is on 14 October.

### Milestone 4: detections

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-14 to 16 | [Detections that fire on real events, and the ones that failed quietly first](2026-10-16-milestone-4-detections.md) | 7, 6, 4, 5, 2, 3 | 12.0 h |

### Web targets on the wire

A parallel track: deliberately vulnerable web applications on their own
segment, attacked from Kali, with a scanner's findings read against the
network sensor's alerts for the same traffic.

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-17 | [A scanner found thirteen problems; the sensor raised thousands of alerts about something else](2026-10-17-web-targets-on-the-wire.md) | 6, 7, 4, 8 | 2.0 h |

### Milestone 5: the RAG app against the OWASP LLM Top 10

Indirect prompt injection first, then a full red-team baseline. Each
experiment measured for what it stops and for what it costs on the honest
questions, with Malcolm counting every request.

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-19 | [Indirect prompt injection, and the one-sentence defense I proved](2026-10-19-milestone-5-indirect-injection.md) | 6, 8, 3, 2 | _tbd_ |
| 2026-10-21 to 22 | [A full red-team baseline of my RAG lab, and what the test taught me about the lab](2026-10-21-milestone-5-red-team-baseline.md) | 6, 8, 7, 3 | _tbd_ |

### Next: the controls, measured

Each control is a setting that can be turned on and off, measured before and
after on the same probes, and for what it costs on the honest questions: an
output cap and a memory limit first, then data delimiting in the prompt, then
an input screen and an output check.

**Reference:** [Searching Malcolm, for someone new to it](searching-malcolm.md).
The query languages, the field names, and the checks to run before
trusting a count, built from the lab's real searches.

**Start here, if the AI architecture is new to you:**
[The whole AI architecture in one place, in order](start-here-ai-architecture.md).
Ten modules from "what the model is" to "how we proved the controls", each one
idea with a check you can run yourself, and a glossary. The references here are
the depth behind it.

**Reference:** [RAG apps: what they are, and how we test them](rag-and-ai-probe.md).
Plain-language architecture — the model versus the knowledge base — and the
data flows an LLM red-team crosses, with diagrams.

**Reference:** [AI guardrails at three budgets, and a checklist that is a jump point](ai-guardrails-and-checklist.md).
What a guardrail is at each of six layers, what to use with no money, a full
vendor stack, or the usual mix, and a build-or-review checklist where every item
is a question, an observable check, and a pointer to the next question.

**Reference:** [Agentic services: the add-on to RAG, and how to secure it the same way](agentic-services.md).
What changes when the model can act: the loop, the tool layer, the two new
rules, the same six places one step right, six places that are new, three
budgets, and the lab add-on written as a plan with its tests.

CISSP domains: 1 Security and Risk Management, 2 Asset Security, 3 Security
Architecture and Engineering, 4 Communication and Network Security,
5 Identity and Access Management, 6 Security Assessment and Testing,
7 Security Operations, 8 Software Development Security.
