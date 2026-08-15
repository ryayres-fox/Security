# Choosing the gateway — control versus convenience

The only genuinely contested decision in the build. Everything else — switch,
AP, sensor, enclosure — is the same either way, and all deep monitoring lives on
the sensor regardless. **So this is the whole decision**, and it is worth
isolating rather than burying in a parts list.

---

## The question, stated properly

Not *"which is better."* Both options are good products and the convenience
option is genuinely excellent at what it does.

The question is: **which capabilities does a self-built monitoring pipeline
actually depend on, and which of those does each option refuse to give you?**

Framed that way, most of the comparison table stops mattering. Four criteria
decided it.

---

## The four that decided it

Marked ★ because they are the ones a monitoring build breaks without. The rest
is preference.

| ★ Criterion | Open gateway (chosen) | Appliance gateway |
|---|---|---|
| **Custom IDS/IPS rules** | Suricata inline, you pick and tune rulesets, per-SID and per-interface | Suricata as a black box — toggle curated categories only. No custom rules, no SID tuning |
| **Log and flow export** | NetFlow/IPFIX, full remote syslog, per-rule logging, resolver query logs, root shell | Flow data stays in the vendor app. No NetFlow/IPFIX, partial syslog, no root |
| **Packages and scripting** | Install anything, plus cron and a full API | Closed appliance. No packages, no official shell, limited API |
| **Firewall granularity** | Per-interface and per-direction rules, floating rules, explicit ordering, aliases, GeoIP, schedules, full NAT | Zone-based — improved, but a simpler model with coarser ordering |

**Export was the decider.** A gateway that cannot ship flow and firewall logs to
a sensor you own is not a component in a monitoring pipeline; it is a separate
product with its own dashboard. The entire point of the build is owning the data
end to end, and that requirement eliminated the appliance before any of the
other criteria were reached.

---

## Where the appliance genuinely wins

A comparison that only flatters the choice you made is marketing.

- **Dashboards out of the box.** Good ones, immediately, with no assembly.
- **Identity and access.** RADIUS, 802.1X, captive portal — genuinely strong,
  and easier to configure than the open equivalent.
- **Auto-updates.** For most people this is a security *feature*. The open
  gateway's "you choose when to update" is only an advantage if you actually do.
- **Time.** The open option costs evenings. That is a real price, and for a
  household network that just needs to be safe and work, the appliance is
  probably the better answer.

**If the goal were a secure home network rather than a monitoring platform, the
appliance would win.** The requirement changed the answer, not the quality.

---

## The tradeoff that is easy to miss

The open gateway hands you the update decision. That reads as control and is
also a **liability**: an appliance that auto-patches beats an open system whose
owner is busy.

The build accepts that trade because the monitoring requirement demands it, and
then mitigates it deliberately — update notifications enabled, and the gateway
OS chosen partly *because* it has the strongest patch cadence in the build (see
[`device-maintenance.md`](device-maintenance.md)).

**Choosing control means accepting an operational obligation.** If you are not
going to meet it, the closed appliance is the more secure choice, and saying so
is not a concession.

---

## The generalisable version

This is the same decision as any build-versus-buy in a security stack, and the
questions transfer directly:

1. **What does the thing you are building actually depend on?** Write the
   requirements before comparing products, or you will compare on features
   neither of you needs.
2. **Which requirement is non-negotiable?** Here: exporting data to a system you
   own. One criterion usually decides it, and the rest of the matrix is
   confirmation.
3. **What obligation does the flexible option create?** Control transfers work to
   you. Budget for it honestly, or take the managed option.
4. **Would the answer change if the requirement changed?** If yes, say so. It
   makes the recommendation credible and it tells the next reader whether it
   applies to them.

A comparison table with twenty rows and no marked criteria is a decision nobody
can re-derive later. Mark the ones that decided it, and record what would have
changed your mind.
