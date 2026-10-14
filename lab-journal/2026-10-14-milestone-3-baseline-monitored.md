# Milestone 3: the RAG baseline, monitored, counted, and still right after a power cycle

| | |
| --- | --- |
| **Time** | About 2.0 h: 1.0 h between 16:35 and 17:35 CDT on 13 October, and 1.0 h between 06:55 and 07:55 CDT on 14 October |
| **CISSP domains** | 7 Security Operations · 6 Security Assessment and Testing · 3 Security Architecture and Engineering |
| **Lab at the start** | The baseline counted three times ([that entry](2026-10-13-rag-baseline-counted.md)). The sensor's clock proven across reboots. target-2 configured, but nothing on it started by itself. |

## What this milestone had to prove

Every request the test harness sends to the RAG app should be seen and
counted. Every box should keep the same clock. And both should still be
true after the lab is shut down and brought back, with nobody fixing
anything by hand.

## Counted four times

The baseline run was 10 questions, 5 times each: 50 requests between
21:15:17 and 21:15:48 UTC on 13 October.

| Count | Result | Where it comes from |
| --- | --- | --- |
| Harness | 50 | its own CSV |
| Gateway | 50 | `nft scan-new` lines from Kali to 10.56.0.22:8080, in that window |
| Zeek | 50 `conn`, 50 `http` | Malcolm's Discover, DQL, absolute window |
| Arkime | 50 sessions | Arkime's own sessions, built from the full packet capture rather than from Zeek |

Arkime is the independent one: it parses the packets itself, so a Zeek
problem would not hide in it.

**The Arkime count was not evidence the first time.** On 13 October I
read "50" off Arkime's Sessions page and moved on. In Malcolm that page
lists Zeek's records too, because Arkime's sessions and Zeek's logs share
one index, so the search I used could not have returned 50 Arkime
sessions. The 50 I saw was most likely the page size, "Showing 1 - 50 of
…". The *Data Source* column, field `event.provider`, tells them apart.
Re-read on 14 October with that filter:

```text
ip.dst == 10.56.0.22 && port.dst == 8080 && event.provider == arkime
Showing 1 - 50 of 50 entries
```

So the count stands, but only since 14 October.

**Nothing was dropped.** Capture loss is not where Discover looks by
default. Malcolm files Zeek's `capture_loss` and `stats` logs with its own
runtime logs, in `malcolm_beats_*`, not with the network records in
`arkime_sessions3-*`. They exist at all only when configure's *Gather
Traffic Capture Statistics* is on, as it was here. The *Packet Capture
Statistics* dashboard reads them. From 16:15 to 16:45 CDT it read 0 packets
dropped in Zeek and in Suricata, and 0 ACKs missed. Zeek saw 33,383 packets and Suricata 26,572. The two
engines count differently, so the drop figures are the ones to compare.

## target-2's clock at boot

After its first clock fix, target-2 still came up 13 s slow and took a
minute to correct. Its own log (CDT) showed why:

```text
17:16:39   Starting systemd-timesyncd
17:16:40   Network configuration changed, trying to establish connection.
17:17:57   Contacted time server 10.56.0.1:123
```

The time service starts before the lab interface can carry a request,
misses, and waits about 65 s before trying again. The fix was one line in
the interface's configuration, so the time service is restarted the moment
the interface is up:

```text
up   systemctl --no-block try-restart systemd-timesyncd.service
```

On the next boot it reached the lab's clock within about a second of the
network coming up.

## target-2 starts itself

Until now, Ollama and Qdrant came back after a reboot only when someone ran
`docker compose up -d`, and the app only while someone kept `serve` open in
a console. One systemd service now does both: compose first, then the app,
logging to the journal and restarting on failure.

The first automatic start showed one more gap. The app was answering at
12:28:23 UTC on 14 October with its clock 12 s slow, and stayed wrong for
41 s, so any audit line written then would carry the wrong time. The fix
makes the app wait for a synced clock, through systemd's
`systemd-time-wait-sync`, capped at 2 minutes so a dead gateway cannot keep
it down for good. The next reboot:

```text
12:33:01   target-2 down
12:33:21   app answering, clock 0 s
```

After each automatic start, 10 real questions came back 10/10 correct. The
health check could not show that: it returns 200 even with the model server
down.

## The night the Mac slept

I left every VM running overnight. The Mac slept anyway, and a sleeping host
freezes every guest. The Mac's own power log showed it waking at 06:53:52
CDT. Then:

- **The gateway, the sensor and target-2 woke 12 h 38 min behind.** The
  gateway's chrony did step its clock, but only at its next poll of the
  internet pool, 10 minutes after the wake. The sensor and target-2 follow
  the gateway, so they were wrong for those 10 minutes too.
- **Kali woke right, and was then pulled wrong.** Its VirtualBox guest
  tools set its clock from the Mac on wake. Then its chrony, with only the
  gateway to ask, took the frozen time as correct and slewed Kali backwards
  toward it. Kali was 65 s slow before I caught it.

Two changes:

1. The gateway re-checks the pool every 64 s at most (`maxpoll 6`), and
   steps whenever it is more than a second out (`makestep 1 -1`). Both
   settings went into Debian's own `chrony.conf` as well as the lab's file,
   so the order the two files are read in cannot undo them.
2. Kali asks three public pool servers besides the gateway. The gateway
   stays preferred, so Kali keeps the lab's time. When the gateway wakes
   wrong, the other three outvote it.

One detail mattered: on Kali the repair was `systemctl restart chrony`, not
`chronyc makestep`. A makestep applies chrony's current estimate, and that
estimate was last night's time.

## Measuring a clock, done properly

I made two measuring mistakes that morning.

- **I measured against Kali.** I compared the sensor and target-2 against
  Kali while Kali itself was being slewed backwards. That made them look as
  if they were creeping back toward the right time, when Kali was the one
  moving.
- **I trusted one outside reference.** GitHub's API `Date:` header turned
  out to lag by 6 to 12 s, by a different amount on each request.

The rule since then is two outside references that agree, Google and
Cloudflare, read in the same second as the box. Every box can be read that
way without logging in. nginx on the sensor and the app on target-2 both
put their host's clock in the `Date:` header of every response.

## Shutting down and coming back

A procedure now covers the whole lab, rehearsed on 14 October:

- **Order:** up is gateway, sensor, Kali, targets; down is the reverse. The
  gateway is every box's route, DNS and clock. The sensor goes down only
  after everything that sends lab traffic is off.
- **From inside:** each VM is shut down with `sudo poweroff`. VirtualBox's
  ACPI power button does nothing on these arm64 Debian VMs.
- **Never** save state, pause, or let the host sleep with VMs running.
- **On the sensor, not Malcolm's `./scripts/stop`.** It removes the
  containers, so nothing comes back at boot.

In the rehearsal the gateway was back 53 s after going down, and Malcolm
answered 75 s after the gateway, with its clock at 0 s. target-2 answered
10/10 by itself. Kali was rebooted last. It came up 13.4 s slow, chrony
stepped it 6 s after starting, and then Kali, the sensor and target-2 all
read 0 s against Google and Cloudflare.

## What to read in the output

| Output | What it tells you |
| --- | --- |
| `chronyc sources` | `^*` is the source in use; `^-` sources are good but not combined. A source far from the others is the one to distrust. |
| chrony's journal | `System clock wrong by N seconds` is chrony finding the gap. `System clock was stepped by N seconds` is the fix. The first line is stamped with the wrong clock and the second with the right one, so a gap of N seconds between them is the step itself, not a wait. |
| A `Date:` header next to two references | A box's clock, read without logging in |
| The service's own journal | Whether a service started at boot, and when |
| Packet Capture Statistics | Dropped packets for Zeek, Suricata and Arkime, per window |

## What I learned

- **A host's sleep is a pause for every guest.** "All the VMs were on" did
  not survive the laptop going to sleep.
- **One time source is a single point of failure even when it is right
  most of the time.** Kali was the one box that woke correct, and following
  a lone wrong source made it wrong.
- **Make the app wait for the clock, not the sensor.** A target losing 20
  seconds of availability costs nothing. A sensor that waits loses the
  packets of its first minute, and the sensor's clock was right at its first
  answer anyway.
- **Measure from outside, with two references.** The box under test can't
  vouch for itself, and neither can one outside server.
- **Count independently.** Four counts from four mechanisms agreeing is
  evidence. One count is a claim.
- **Read the total, not the page.** A list view's first number is often
  its page size. "50 per page" and "50 entries" look alike at a glance.

## Next

Milestone 4: detections. Kali gets a firewall that logs every new inbound
flow on the management network and ships its logs to Malcolm. The first
alert rules come next, tested against a real case: a Python web server left
running on Kali and reached from the Mac, which nothing recorded the first
time.
