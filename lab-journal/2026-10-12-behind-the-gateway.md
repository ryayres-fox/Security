# 2026-10-12: Kali is behind the gateway, checked from inside Kali

| | |
| --- | --- |
| **Time** | About 0.5 h, the morning of 12 October (CDT) |
| **CISSP domains** | 4 Communication and Network Security · 7 Security Operations · 6 Security Assessment and Testing |
| **Lab at the start** | The gateway built and verified the day before. Kali rewired behind it at the end of the last session: two adapters, no NAT, an evidence disk, its clock from the lab. The sensor and the targets not yet up. |

## The goal

Before the next build step, read the lab's state from the workstation
itself. The runbook says what Kali should look like behind the gateway.
This session asks the box.

## Every packet leaves through the gateway

```bash
ip -br addr
# lab    UP  10.56.0.10/30
# mgmt   UP  192.168.56.10/24
# docker0 DOWN 172.17.0.1/16

ip route
# default via 10.56.0.9 dev lab proto static metric 102
# 10.56.0.8/30 dev lab proto kernel scope link src 10.56.0.10 metric 102
# 192.168.56.0/24 dev mgmt proto kernel scope link src 192.168.56.10 metric 103

ip route | grep -c '^default'      # 1
ip route get 10.56.0.18            # 10.56.0.18 via 10.56.0.9 dev lab src 10.56.0.10
ping -c 2 -W 2 10.56.0.9           # 2 received, 0% packet loss
```

One default route, through the gateway. The target segment is routed, not
on-link. The internet still works, which means the gateway's egress rule
for Kali works:

```bash
curl -sS -o /dev/null -w "github.com %{http_code} %{time_total}s\n" https://github.com
# github.com 200 0.498131s
curl -sS -o /dev/null -w "pypi.org %{http_code} %{time_total}s\n" https://pypi.org/simple/
# pypi.org 200 3.577371s
getent hosts github.com            # an address, resolved by 10.56.0.1
```

On the management network, the Mac and the gateway answered. The sensor
did not, which was expected: it was not built yet.

```bash
for h in 192.168.56.1 192.168.56.2 192.168.56.5; do ping -c 1 -W 1 $h >/dev/null 2>&1 && echo "$h up" || echo "$h no reply"; done
# 192.168.56.1 up
# 192.168.56.2 up
# 192.168.56.5 no reply
```

## The forwarding control is Docker's, not the sysctl

The runbook turns IP forwarding off on Kali, so a box with a foot on both
the lab and the management network cannot route between them. The sysctl
read 1.

```bash
cat /proc/sys/net/ipv4/ip_forward   # 1
systemctl is-active docker          # active
```

Docker enables forwarding when it starts. What still stops Kali from
routing is the policy Docker installs with it, `FORWARD DROP`. That
morning I had changed the runbook so the check reads the policy, not the
sysctl:

```bash
sudo iptables -S FORWARD | head -1   # -P FORWARD DROP
```

I could not read it back in this session. The check needs sudo, and the
shell I ran it from had no password. It stays unverified here, and is the
first line of the next session.

## Clock and evidence disk

```bash
chronyc sources
# ^* 10.56.0.1   3   6   377    12    -48us[  -50us] +/-   19ms
timedatectl | grep synchronized
# System clock synchronized: yes
findmnt /evidence
# /evidence /dev/sdb ext4 rw,noatime
echo $SQUAWK_ROOT
# /evidence
```

Kali takes its time from the lab's clock on the gateway. The evidence
disk is mounted, and the scanner writes there.

## A clone with no identity

The public repository's clone on Kali had neither the pre-commit hook
path its contributing guide asks for nor a commit identity. A commit made
from it would have carried a wrong author or failed outright.

```bash
git -C ~/Security config core.hooksPath   # (empty)
git -C ~/Security config user.email       # (empty)
git config --global user.email            # (empty)
```

Not changed in this session. The identity is mine to set.

## What I learned

- **A control that lives in a sysctl can be overridden by a daemon.**
  Docker sets `ip_forward` on start. The real control is the FORWARD
  policy, and the check has to read that.
- **Verify from the box, not from the plan.** The plan said Phase 5 was
  next. The box said it was done: two adapters, one route, the lab's
  clock. Six minutes of reads saved a wasted sitting.
- **A gate that needs sudo is not a gate my tooling can run.** Say so in
  the log rather than writing "verified".

## Next

1. Read `sudo iptables -S FORWARD | head -1` on Kali by hand.
2. Set the hook path and the commit identity on the public repository's
   clone.
3. Build the sensor on the mirror network, Part 3 of the runbook.
