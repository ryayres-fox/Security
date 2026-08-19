# Build guide

Phased so the household stays online throughout, insight arrives in week one,
and every cutover is small and reversible.

**Total: ~$1,980 pre-tax** (mid-2026, 1G WAN). But the ordering matters more than
the total, because **the first $872 delivers the monitoring** and the rest buys
control and segmentation. If the budget stops after Wave 1, you still have a
working NSM platform.

---

## Purchase order

| Wave | Buy | Cost | Why this order |
| --- | --- | ---: | --- |
| **1 — Insight** | 2.5G PoE switch · fanless N100 sensor + 32GB RAM + 256GB & 2TB NVMe · UPS · Cat6 | **$872** | Full visibility on the *existing* network. No router change, so no downtime risk |
| **2 — Gateway** | Fanless x86 appliance + 16GB RAM + 512GB NVMe | **$504** | The one real cutover. VLAN routing, inline IPS, log export. Old router kept as rollback |
| **3 — Wireless** | WiFi 7 AP | **$279** | WiFi last. Run both APs briefly, then retire the old router |
| **Anytime — Enclosure** | Cabinet · active cooling · vented shelves · PDU | **$325** | After everything works. Do not fight a rack mid-troubleshoot |

Buy the **UPS in Wave 1** so the sensor and switch are protected from day one —
a sensor that loses power mid-write is a corrupt index and a gap in the data you
built the thing to collect.

---

## Phase 0 — Prep (free, while the gear ships)

The phase that pays off most, and it costs nothing.

- **Map what you have.** Every wired device and its port, the DHCP range, port
  forwards, DNS. You cannot verify a migration against a baseline you never took.
- **Draft the VLAN plan on paper.** Trusted / AV / Gaming / IoT / Guest / Mgmt.
- **Build the configs in VMs.** Install the gateway OS in a VM and pre-build WAN,
  LAN, VLANs, firewall rules and the resolver. Run Zeek and Suricata in Docker to
  learn the tooling.

That last one is the single biggest accelerator. You arrive at each cutover with
**tested configuration instead of improvisation**, and the expensive part of a
cutover was never the hardware — it is discovering at 11pm that you do not know
the syntax.

---

## Phase 1 — Insight, with zero disruption

1. Stand up the **sensor** — Zeek, Suricata, DNS metadata, enrichment.
2. **Insert the switch at layer 2**: router LAN port → switch uplink → devices.
   The router still does DHCP, routing and WiFi. The network stays flat and
   behaviourally unchanged.
3. **Mirror the switch uplink to the sensor.** You now see all wired and
   internet-bound traffic.
4. **Let it bake.** Tune Suricata, build dashboards, establish baselines.

> **This is the phase worth copying.** It is a pure additive insertion — if
> anything acts up, plug the devices back into the router and you are exactly
> where you started. You get working visibility *before* touching the thing the
> household depends on, for under half the budget.

No VLANs yet; the consumer router cannot route them. That is fine — you are
gathering visibility, and segmentation arrives with the gateway.

---

## Phase 2 — Gateway cutover

The only genuinely risky step, so it is a single swap with a five-minute rollback.

1. Load the **pre-tested config** onto the appliance.
2. In a low-usage window: modem → gateway WAN, gateway LAN trunk → switch, move
   DHCP across. One clean swap.
3. **Keep the old router on a shelf.** If anything is wrong, move one cable back.
4. Point gateway firewall, DNS and NetFlow logs at the sensor. Re-aim the SPAN to
   catch inter-VLAN traffic as well as the uplink.

---

## Phase 3 — Segmentation, one VLAN at a time

- Create the VLANs but **keep the existing flat subnet as "Trusted"** so nothing
  breaks on day one.
- Migrate **least-risky first**: a test device, then IoT, then AV, gaming, guest,
  management. Verify each before the next.
- Stand up an **mDNS reflector, scoped** to the two VLANs that need it, when
  media devices move. This is where most home segmentation projects stall — Sonos
  and AirPlay assume a flat network, and the fix is a scoped reflector rather
  than abandoning the VLAN.
- Each device move is independently reversible.

---

## Phase 4 — WiFi, and retiring the weak link

1. Bring up the new AP and map **SSID → VLAN**.
2. **Run both APs in parallel** briefly to confirm coverage and roaming.
3. Turn off the old router's radio, then retire it entirely.

The old router is the last thing removed because it is both the rollback and —
per [`device-maintenance.md`](device-maintenance.md) — the least maintainable
device in the build. It leaves once nothing depends on it.

---

## Phase 5 — Enclosure and polish

Move everything into the cabinet **after** it is validated. Cable management
during troubleshooting is how a two-hour problem becomes a weekend.

---

## What you actually get, and when

| Milestone | Spend | Capability |
| --- | ---: | --- |
| End of Phase 1 | **$872** | Zeek + Suricata + DNS with enrichment. Full wired visibility |
| End of Phase 2 | $1,376 | \+ inline IPS, VLAN routing, gateway log export |
| End of Phase 4 | $1,655 | \+ segmentation, clean SSID→VLAN mapping, weak link retired |
| End of Phase 5 | $1,980 | \+ enclosure, cooling, cable management |

---

## If your budget is smaller

The sequencing is designed to be stopped at any wave, which is not an accident —
it is the same property that makes a migration plan safe.

- **~$450:** sensor + a cheaper managed switch with port mirroring. Visibility
  only, no segmentation. **Still the best value in the whole build.**
- **~$870:** Wave 1 complete. Add the UPS and better storage.
- **~$1,380:** add the gateway. This is where segmentation and inline IPS start.

If you only ever do one thing, do the SPAN and the sensor. Everything else is
control; that is knowledge.

---

## The transferable part

Strip out the part numbers and this is a production migration plan:

1. **Instrument before you change anything.**
2. **Keep the previous system as the rollback until the new one has proven
   itself** — not until it is installed.
3. **Test the configuration somewhere free before the window.**
4. **Migrate least-risky first**, and make each step independently reversible.
5. **Do the cosmetic work last.**

Slow is smooth, and smooth is fast.
