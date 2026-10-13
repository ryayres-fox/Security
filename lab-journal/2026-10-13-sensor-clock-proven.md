# 2026-10-13: Proving the sensor's clock comes back, and the package that stopped it

| | |
| --- | --- |
| **Time** | About 1.5 h, between 13:30 and 15:55 CDT |
| **CISSP domains** | 7 Security Operations · 6 Security Assessment and Testing · 3 Security Architecture and Engineering |
| **Lab at the start** | The sensor's clock set by hand that morning ([that entry](2026-10-13-sensor-clock.md)). No time source of its own yet. |

## The goal

Give the sensor a clock that survives a pause and a reboot with nobody
touching it, and prove it by measuring from outside the box.

## The measurement

From Kali, every 5 seconds, the sensor's nginx `Date:` header against
Kali's own clock:

```bash
curl -sk --max-time 3 -D - -o /dev/null https://192.168.56.5/ | grep -i '^date:'
```

It runs outside the sensor on purpose. A check run on the sensor can change
what it measures, and today one did (below).

## What went in

**On the gateway:**

- chrony answers the sensor: `allow 192.168.56.5`.
- One input rule admits NTP from the sensor's address only.
- `makestep 1 -1` is now in the file, read back as
  `/etc/chrony/conf.d/lab.conf:13`.

`sudo chronyc clients` then listed `192.168.56.5` asking.

**On the sensor:**

- A host route to the lab clock, `10.56.0.1/32 via 192.168.56.2`, written
  into `/etc/network/interfaces` so it survives a reboot.
- systemd-timesyncd, which Debian already ships, pointed at `10.56.0.1`
  with `PollIntervalMaxSec=64`.
- Malcolm's restart policy set to `unless-stopped`: all 27 services in the
  compose file, and all 27 running containers through `docker update`, so
  Malcolm did not have to restart.

I chose timesyncd over chrony because installing chrony would have meant
putting the sensor on the internet. A sensor should not have that path.

## Test 1: a two-minute pause

```bash
VBoxManage controlvm "sensor" pause && sleep 120 && VBoxManage controlvm "sensor" resume
```

| UTC | Sensor's offset, read from Kali |
| --- | --- |
| 19:58:54 | −132 s (the pause, plus a 12 s one a few seconds before it) |
| 19:59:39 | 0 |

timesyncd stepped the clock back 40 to 45 seconds after the resume, with
nobody touching the sensor.

## Test 2: reboots

Malcolm came back on its own every time. Nobody ran `./scripts/start`.
443 was down 47 to 82 seconds per reboot, most of it Docker stopping 27
containers on the way down, and it answered within seconds of the network
coming back. After the first reboot, 27 of 27 containers were running and
healthy.

The clock did not come back. Each boot started 12 to 15 seconds slow and
stayed there. After the third reboot it sat at −15 s for more than 12
minutes.

## The package that stopped it

`systemctl status systemd-timesyncd` said `enabled`, `inactive (dead)`, and
showed no failed condition. The boot log had no line about it at all. This
did:

```bash
systemctl show systemd-timesyncd -p ConflictedBy -p ConditionTimestamp
# ConflictedBy=vboxadd-service.service
# ConditionTimestamp=          (empty: systemd never tried to start it)
```

VirtualBox Guest Additions 7.2.18 were installed on the sensor. Their
`vboxadd-service` unit declares a conflict with systemd-timesyncd, because
it syncs time itself.

At boot, systemd started `vboxadd-service` and dropped timesyncd without
logging anything about it. `vboxadd-service` then failed. Its kernel module
could not be built, because the sensor has no kernel headers and no
internet to fetch them:

```text
[    3.595070] vboxadd: Kernel headers not found for target kernel 6.12.111+deb13-arm64.
[    3.665983] vboxadd: unable to load vboxguest kernel module, see dmesg
[    3.681395] systemd[1]: Starting vboxadd-service.service...
```

So the sensor got no time sync at all, from a package that did nothing
else.

`systemctl disable` did not hold: on the next boot both services still read
`enabled`. `systemctl mask` did:

```bash
sudo systemctl mask vboxadd vboxadd-service
systemctl is-enabled vboxadd vboxadd-service   # masked masked
```

The next boot, from the sensor's log:

```text
[    1.593774] Starting systemd-timesyncd.service - Network Time Synchronization...
[    2.593075] systemd-timesyncd: Network configuration changed, trying to establish connection.
[   66.825983] systemd-timesyncd: Contacted time server 10.56.0.1:123 (10.56.0.1).
[   66.827557] systemd-timesyncd: Initial clock synchronization to Tue 2026-10-13 15:49:41.601038 CDT.
```

From Kali, 443 came back at 20:48:43 UTC with the clock 13 s slow, and the
clock read 0 at 20:49:43. That was the first boot of the day where the
sensor set its own time.

## The check that hid it

`timedatectl timesync-status` asks timesyncd for its status over D-Bus, and
asking starts the service. Run after a boot, it reports a synced clock a
few seconds later and looks healthy, because it fixed what it was checking.

That happened once today. The log shows timesyncd starting at 15:07:54,
three minutes after the first reboot, at the moment that check ran. Only
the outside measurement showed the three minutes before it.

## The minute after boot, closed

timesyncd starts 1.6 seconds into boot, before the route to the lab clock
is up. It gets nothing back, and its next try comes about 64 seconds later,
so for that minute Malcolm's records carried a 12 to 15 second error. One
line in the sensor's `/etc/network/interfaces`, right after the route,
restarts timesyncd the moment the route exists:

```text
up   ip route add 10.56.0.1/32 via 192.168.56.2 dev $IFACE
up   systemctl --no-block try-restart systemd-timesyncd.service
```

The Guest Additions were uninstalled in the same pass (`uninstall rc=0`).
The next reboot, from Kali:

```text
21:04:07   443 down
21:04:55   443 back, offset 0 s
21:05:16   offset 0 s
```

The clock was right at the first answer.

## What to read in the output

| Output | What it tells you |
| --- | --- |
| `systemctl show <unit> -p ConflictedBy` | The units that will stop this one from starting. For a sensor's time service, empty is the answer you want. |
| `ConditionTimestamp=` empty | systemd never tried to start the unit this boot. A failed condition carries a time and `ConditionResult=no`. |
| `ActiveEnterTimestamp=` | When the unit last started. Compare it with the boot time. |
| `journalctl -b -o short-monotonic` | Seconds since boot, which puts the order in view: timesyncd at 1.6 s, its first contact at 66.8 s. |
| The `Date:` offset, read from outside | The one number here that checking cannot change. |

## What I learned

- **A check can start the thing it checks.** `timedatectl timesync-status`
  activates timesyncd. Measure from outside the box when the question is
  whether something runs on its own.
- **Enabled is not the same as started.** A unit can be enabled, have no
  failed conditions, and never run, because another unit conflicts with
  it. Nothing about it is logged.
- **Disable is a preference, and mask is a gate.** The disable did not
  survive a boot. The mask did.
- **Remove what a box does not use.** On the sensor, the Guest Additions'
  only effect was to stop its clock.
- **The restart policy is Malcolm's cheapest availability control.** Its
  default is `no`. With `unless-stopped`, five reboots needed no hands.

## Next

1. Run the RAG baseline again with the sensor up, and count it three
   times: harness, gateway, Malcolm. Done in
   [the next entry](2026-10-13-rag-baseline-counted.md).
