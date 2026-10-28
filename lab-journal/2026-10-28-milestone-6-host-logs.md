# Milestone 6: the targets' host logs, and a certificate per host

| | |
| --- | --- |
| **Time** | About 4 h across 27 and 28 October 2026, the second day mostly the per-host certificate and the verification in the SIEM |
| **CISSP domains** | 7 Security Operations · 6 Security Assessment and Testing · 4 Communication and Network Security · 5 Identity and Access Management · 3 Security Architecture and Engineering |
| **Lab at the start** | Detections firing on real events, the workstation and gateway firewall logs reaching the SIEM, time correct across power cycles ([that entry](2026-10-16-milestone-4-detections.md)). The targets themselves sent nothing but what crossed the wire, and every forwarder shared one client certificate. |

## What this milestone had to prove

A target is invisible once a shell lands on it. The network sensor sees
packets — who connected to what — but not who logged in, who used sudo, or
what command they ran. So the first thing to prove was a target's **host**
log reaching the SIEM: the identity events, centralised, searchable. The
second was doing it **without giving the target a path into the management
plane**, which the whole lab is built to deny. The third was getting the
forwarders off a **shared** certificate, each onto one of its own.

## The coverage gap

Before shipping anything, I mapped the lab's telemetry source by source
against three public references: the CISA/ASD/NSA/FBI *Best Practices for
Event Logging and Threat Detection* (2024) factors, OMB M-21-31's maturity
tiers (EL0–EL3), and NIST 800-53's AU family. The network plane was strong —
flow, DNS, HTTP and TLS metadata, IDS alerts, full session capture — and the
firewall logs from the workstation and the gateway were centralised. The gap
was **host, application and identity**: the targets ship no OS logs, the
application's audit log is local to its box, and the identity provider records
its logins only in its own container, not in the SIEM. Centralisation (EL1)
was only partial.

The useful distinction: a log can be **generated**, **centralised**, or
**searchable and retained** — three different states. "The app logs it" is not
"we can see it." Each gap was verified on the box — the service inactive, the
audit file found and local, the container log read — not assumed.

## Centralise without breaking isolation

Here is the real design conflict. The targets are deliberately kept off the
management plane: a compromised target must not be able to reach the sensor.
But centralising a target's logs **needs** a path to the sensor. Centralise
and isolate pull against each other.

The answer is not "put the target on the management network" — that throws away
the isolation. It is a **narrow, audited, one-way telemetry pinhole**: allow
only `target → sensor`, on the single log port, and log every new flow; then
**masquerade** that flow at the gateway so the management-only sensor can
*answer* without being given any route back into the lab. The net effect is
that the sensor still cannot *initiate* a connection into the lab — the
isolation is intact — but it can *answer* the target's log stream. And the
firewall hole only lets the target **try**: the TLS client certificate is the
real authentication.

The evidence found the fault for me. The gateway's own firewall log recorded a
line for every forwarded connection attempt, and a connection that retried with
no reply pointed straight at a return-path problem — the sensor had no way to
answer — which the masquerade fixed. Reading the log located the fault; I did
not have to guess.

## A certificate per host

The forwarders had all been sharing one client certificate. That is a real
weakness: any host holding the shared pair could pose as the sensor to another
forwarder that checks only the signing CA, and one leaked key cannot be revoked
without re-issuing for everyone. A certificate **per host** is the point of this
milestone.

I nearly shipped the target on the shared certificate anyway, and the mistake is
worth recording. I searched for the CA's signing key under one service's
certificate directory, found only the public certificate, and concluded we could
not sign our own without standing up a CA — which the host's owner had asked not
to take on. **Both halves of that were wrong.** The signing key was there, one
directory over, under a different service's certificates; a single CA signs for
all of them, which a fingerprint check confirmed — the certificates share one.
And **"use the existing CA to sign one certificate" is not "run a CA."** Signing
is a one-time command with the key that already exists; it carries no renewal
service, no new trust root, no operational burden. I had conflated the two and
let it steer a weaker design. Corrected.

Done properly, target-2's key is **made on the box and never leaves it**;
only the signing request and the signed certificate cross the network,
couriered by Kali because target-2 can reach the sensor on the one
log port only — it cannot serve a request back the way the other hosts did. The
certificate names the host in its organisational-unit field, is marked for
client authentication, and is signed by the lab CA. The go/no-go before
installing it was a fingerprint comparison: the CA that signed the certificate
is the **same** CA the log listener trusts. Then the shared pair was deleted
from the box.

## What the host log shows

With target-2 on its own certificate, its authentication journal reaches the
SIEM: a session opened and closed, the account that escalated, and the **exact
command run under sudo** — each record attributed to the host. That is the gap
closed for target-2, the first of the two targets. An attacker who lands a
shell, invisible on the wire, now leaves a trail on a collector they do not control. A marker line and
the real sudo records from a service restart appeared in the SIEM within about
ten seconds, attributed by the host-name field the agent sets — not by the
certificate. The certificate decides *who may send at all*; the field decides
*whose* the log is.

## What I learned

- **Search the whole tree.** The CA's signing key was one directory from where I
  looked. A narrow search became a wrong conclusion and nearly a worse design;
  the fix was to widen the search, not to work around the absence.
- **"Use a CA" is not "run a CA."** Signing one certificate with a CA that
  already exists is a single step. Treating it as operational overhead almost
  cost this milestone its entire purpose.
- **Centralise and isolate can both hold.** The answer to "an isolated host must
  reach the collector" was a one-way, logged, authenticated pinhole with a
  masquerade for the return path — not a gap in the isolation.
- **A shared credential is a blast-radius decision.** One certificate for every
  forwarder is convenient and impossible to revoke singly; a certificate per
  host costs one signing step and contains a leak to one host.
- **Authentication and attribution are different layers.** The certificate
  decides who may send; the record's own host field decides whose log it is. The
  transport does not need to carry identity, but it still gates who connects.

## What to read in the output

| Output | What it tells you |
| --- | --- |
| A telemetry-pinhole log line on the gateway | the target's log flow is leaving for the sensor, and the firewall counted it |
| A repeated connection attempt with no reply | a return-path problem, not the application — here, the sensor had no route to answer until the masquerade |
| Two certificate fingerprints that match | the CA that signed a client certificate is the one the listener trusts, so it will be accepted |
| A host-name field on a forwarded record | which box the log is from — set by the agent, independent of the certificate |
| A sudo record with its `COMMAND` | the host-level identity event the network sensor cannot see at all |

## Next

target-1 by the same pattern, now proven. A **server** certificate of
the sensor's own, so a forwarder verifies the sensor's identity and not only its
CA. And the application's audit log and the identity provider's logins, which
are still local — the remainder of the host and identity gap this milestone
opened.
