# Can you keep it patched? — a pre-purchase assessment

Every device in the build, assessed against three years of CVE history and its
vendor's *actual* patch behaviour — **before** any of it was bought.

> **Dated artifact.** Assessed 2026-06-13 against vendor PSIRTs, NVD records and
> firmware pages. Specific CVE identifiers age fast and should be re-verified
> before you rely on them. The **method** and the **verdicts** are the durable
> part, and they are what this document is for.

---

## Why bother

The usual home-lab purchase decision is throughput, ports, price, noise. Nobody
asks the question that determines whether the thing is still safe in three
years:

> **Does this vendor actually ship security fixes, how fast, and how would I
> know?**

It is worth asking because the answer varies enormously between devices that
look equivalent on a spec sheet — and because it changes **which role a device
should get**, not just whether to buy it.

This is the same diligence you would apply to a third-party dependency at work.
Most people apply it to npm packages and not to the box their whole network runs
through.

---

## The finding that changed the design

The cheapest sensor hardware — a generic ODM mini-PC — has **no formal PSIRT and
no coherent patch channel.** Firmware updates are distributed informally through
a vendor forum and messaging app. It is a standard Intel + AMI board, so it
*inherits* BIOS-class issues (Secure Boot key leaks, UEFI image-parser RCEs,
microcode advisories) **without a guaranteed pipeline to fix them.**

That does not make it unusable. It makes it unusable **as the gateway**:

| Role | Verdict | Reasoning |
|---|---|---|
| **Sensor** | Acceptable | Passive, behind the firewall, no inbound exposure. The OS carries the security weight and applies microcode |
| **Gateway** | **No** | The gateway *is* the security boundary. A boundary device with no patch channel is not a boundary |

So the build uses two different mini-PCs — a cheap one for the sensor, a
firmware-maintained one for the gateway — and the **$150 price difference buys a
patch pipeline**, which is the actual product being purchased.

**That is the transferable idea.** Patch cadence is not a tiebreaker to consider
after you have chosen; it is an input that determines where a component is
allowed to sit in the architecture.

---

## The assessment

| Device | Role | CVE history | Patch cadence | Verdict |
|---|---|---|---|---|
| **Gateway OS** (OPNsense) | Security boundary | Several, incl. critical RCE | **Excellent** — biweekly minors, fixes in hours to days, full advisories | ✅ Best-maintained component in the build |
| **Gateway hardware** | Boundary hardware | Industry-wide firmware issue, vendor responded | Good — open firmware option, field-flashable | ✅ Run the open firmware; smaller attack surface |
| **Managed switch** | LAN + SPAN | Multiple, incl. critical takeover | Good — active release train | ✅ Fine **if** management interfaces are restricted to the mgmt VLAN |
| **Sensor hardware** | Passive sensor | Inherits BIOS-class issues | **Weak** — informal, no PSIRT | ⚠️ Sensor only. Not the gateway |
| **Reused consumer router** | AP (temporary) | Vendor-wide advisory stream, plus an auth-bypass class | Slow, closed, no published EOL | ⚠️ **Weakest link.** AP only, retire within 1–2 years |
| **WiFi AP + controller** | Wireless | Recurring high/critical in the *controller* | Fast — ships emergency fixes | ✅ Good cadence; patch the controller promptly, keep it on mgmt |

---

## Three patterns worth carrying to work

**1. The recurring theme is exposed management interfaces.**
Most of the switch's serious CVEs are reachable only through management
protocols. In this design the switch is a LAN device on a management VLAN and
never internet-facing, which neutralises the majority of them. **The
architecture, not the patch level, is doing most of the work** — and that is the
argument for segmentation that a CVE list makes better than any policy document.

**2. The controller is a bigger target than the device.**
For the wireless vendor, the critical findings cluster in the *management
application*, not the access points. The thing that manages your fleet is more
valuable than any single member of it, and it usually has a larger attack
surface and a web UI. Patch the controller first.

**3. "Still getting updates" is not the same as "will be."**
The consumer router had received firmware within the last year, which reads as
healthy. It is also six years old, closed, and has **no published end-of-life
date** — so there is no way to plan around its retirement, which is exactly why
the build schedules its removal rather than waiting for updates to stop.

An unpublished EOL is a maintenance risk in itself. You cannot manage a deadline
nobody will tell you.

---

## How to run this yourself

Half a day, before you spend anything:

1. **List candidate devices by role.** Boundary devices get the strictest bar.
2. **Search NVD for three years of history** per vendor and product line. You are
   not looking for zero CVEs — that usually means nobody is looking. You want
   evidence that findings get *fixed*.
3. **Find the PSIRT page.** If there isn't one, that is the finding.
4. **Time the last few fixes.** Advisory date to firmware availability. Days is
   good. "We do not publish that" is an answer.
5. **Check for a published EOL.** No date means no plan.
6. **Then assign roles.** Let the weakest-maintained device take the least
   security-relevant position — or leave it out.

The output is one line per device: *can I keep this patched, how fast, and how
will I find out?* If you cannot answer for a device that terminates your WAN,
buy a different one.

---

## What this does not cover

Supply-chain compromise of the firmware itself, hardware implants, and vendor
compromise. Those are real and out of scope for a home build — the mitigation
available here is preferring open firmware where it exists and keeping the
boundary device on a vendor that publishes advisories at all.
