# Home lab — a network security monitoring build

A designed, costed and sequenced build for a home NSM platform: open gateway,
VLAN segmentation, and an out-of-band Zeek/Suricata/DNS sensor.

**What this is:** the design, the purchase order, the deployment sequence, and a
pre-purchase maintenance assessment. **What it is not:** a war story. Where a
phase has been executed the notes say so; where it has not, they say that too.

**Sanitized.** No addresses, hostnames, SSIDs or captured data. The gear, the
prices and the reasoning are the useful part and none of it is sensitive.

![Network architecture](network-diagram.svg)

---

## Why it exists

The starting point was a consumer WiFi router that is a perfectly good router and
a useless security telemetry source:

- **No remote syslog.** Logs are viewable in the web UI or emailed as a digest.
  A firmware design limit, not a missed setting.
- **No NetFlow/IPFIX.** No flow export of any kind.
- **No port mirroring.** Nothing to tap for a sensor.
- **No viable third-party firmware.** Broadcom-based; OpenWrt/DD-WRT support is
  effectively nonexistent, so you cannot flash your way out.

That is the whole problem statement, and it generalises: **most home gear cannot
be a log source, and no amount of configuration changes that.** The fix is to
demote it to an access point and put something in front of it that can export.

---

## What is here

| | For someone who wants to |
| --- | --- |
| [`build-guide.md`](build-guide.md) | **Build this.** Phased purchase order with prices, and a deployment sequence where every step is reversible |
| [`gateway-decision.md`](gateway-decision.md) | **Choose a gateway.** The control-versus-convenience tradeoff, with the criteria that actually decided it |
| [`device-maintenance.md`](device-maintenance.md) | **Not regret it in three years.** CVE history and patch cadence per device, assessed *before* buying |
| [`architecture.md`](architecture.md) | Understand the segmentation and the monitoring pipeline |
| [`detection-engineering.md`](detection-engineering.md) | See the detections and how they map to ATT&CK |

---

## The three ideas worth stealing

Most home-lab writeups are a parts list and a diagram. These are the parts that
transfer to work, and they are why this is in a security-engineering portfolio.

**1. Buy insight before you buy change.**
Wave 1 is a switch, a sensor and a UPS — **$872, under half the budget** — and it
delivers full traffic visibility with *zero* change to how the network routes.
The switch goes in at layer 2 between the existing router and the wired devices;
the sensor takes a SPAN of the uplink. If anything misbehaves, plug the devices
back into the router and you are exactly where you started.

You get Zeek, Suricata and DNS metadata, and time to tune them, **before** you
touch the thing the household depends on. The same instinct applies to a
production migration: instrument first, change second.

**2. Keep the old thing as the rollback.**
The consumer router is not retired until the last phase. Through the gateway
cutover it sits on a shelf, and rollback is moving one cable — about five
minutes. It is only decommissioned once the replacement has proven itself
through a full segmentation rollout.

**3. Check the patch cadence before you buy, not after.**
[`device-maintenance.md`](device-maintenance.md) assesses every candidate device
against three years of CVE history and its vendor's actual patch behaviour. That
turned up a real result: the cheapest sensor hardware has **no coherent patch
channel** — updates are distributed ad hoc through a vendor forum — which is
tolerable for a sensor on a management VLAN and would be disqualifying for a
gateway.

Almost nobody does this before spending the money, and it is the closest thing
here to real supply-chain diligence.

---

## Honest scope

Metadata monitoring only. No packet decryption, no endpoint agents, no full
PCAP — Zeek, Suricata and DNS logs with GeoIP/ASN/intel/JA4 enrichment applied
in stream. That is a deliberate limit, and it means encrypted payloads are
opaque and anything that never crosses the tap is invisible.

Prices are mid-2026 estimates for a 1G WAN. Re-verify before ordering; the
sequencing is the durable part, not the part numbers.
