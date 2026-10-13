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
  with the result it should give. The addresses are the lab's own plan
  (RFC 1918), on a VirtualBox host-only network and internal networks.
  None of it can be reached from anywhere else.
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

| Date | Entry | CISSP domains | Time |
| --- | --- | --- | --- |
| 2026-10-12 | [Kali is behind the gateway, checked from inside Kali](2026-10-12-behind-the-gateway.md) | 4, 7, 6 | 0.5 h |
| 2026-10-13 | [The gateway was thirteen hours behind, and every clock I could read from outside it said it was fine](2026-10-13-gateway-clock-dns.md) | 4, 7, 6, 3 | 1.5 h |
| 2026-10-13 | [The sensor was capturing, and its clock was twelve hours behind](2026-10-13-sensor-clock.md) | 7, 4, 6, 3 | 1.5 h |
| 2026-10-13 | [Proving the sensor's clock comes back, and the package that stopped it](2026-10-13-sensor-clock-proven.md) | 7, 6, 3 | 1.5 h |

The first two 2026-10-13 entries shared one morning, 09:15 to 12:45 CDT,
and split its time between them: 3.0 h, counted once. The afternoon entry
adds 1.5 h, for 4.5 h that day.

CISSP domains: 1 Security and Risk Management, 2 Asset Security, 3 Security
Architecture and Engineering, 4 Communication and Network Security,
5 Identity and Access Management, 6 Security Assessment and Testing,
7 Security Operations, 8 Software Development Security.
