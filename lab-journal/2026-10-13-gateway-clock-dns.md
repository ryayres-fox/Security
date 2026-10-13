# 2026-10-13: The gateway was thirteen hours behind, and every clock I could read from outside it said it was fine

| | |
| --- | --- |
| **Time** | About 1.5 h, between 09:15 and 12:15 CDT, alongside the [sensor entry](2026-10-13-sensor-clock.md) |
| **CISSP domains** | 4 Communication and Network Security · 7 Security Operations · 6 Security Assessment and Testing · 3 Security Architecture and Engineering |
| **Lab at the start** | Gateway, Kali and target-2 verified. The RAG baseline had run at 09:00 that morning: 50 of 50 honest answers, committed on Kali and not yet pushed. The sensor was being brought up in another window; that story is [its own entry](2026-10-13-sensor-clock.md). |

## The goal

Push the baseline, then start down the RAG lab's verification plan from
the target's operating system up. The middle of the morning went to a DNS
fault that turned out to be a clock.

## Images for the container layer, pulled and scanned on Kali

The plan's layer 5 wants each pinned image scanned on Kali and its ID
compared with the target's copy.

```bash
docker pull qdrant/qdrant:v1.19.2-unprivileged   # rc=0
docker pull ollama/ollama:0.40.2                 # rc=0
docker image inspect --format '{{.RepoTags}} {{.Architecture}} {{.Id}}' qdrant/qdrant:v1.19.2-unprivileged ollama/ollama:0.40.2
# [qdrant/qdrant:v1.19.2-unprivileged] arm64 sha256:78f74e6b2188...
# [ollama/ollama:0.40.2] arm64 sha256:035ba91edf20...
trivy image --scanners vuln qdrant/qdrant:v1.19.2-unprivileged
# qdrant/qdrant:v1.19.2-unprivileged (debian 13.7): Total: 165 (LOW 60, MEDIUM 58, HIGH 44, CRITICAL 0)
# Node.js (node-pkg): Total: 9 (MEDIUM 3, HIGH 4, CRITICAL 2)
trivy image --scanners vuln ollama/ollama:0.40.2
# ollama/ollama:0.40.2 (ubuntu 24.04): Total: 29 (LOW 7, MEDIUM 22, HIGH 0, CRITICAL 0)
# (library findings): Total: 93 (LOW 3, MEDIUM 34, HIGH 47, CRITICAL 0)
```

The comparison with target-2's IDs is a console step on the target, not
done yet. Neither do the findings have a triage yet. Both images run
loopback-only on a target with no internet (layer 7, below). That limits
who can reach them, not what is in them.

## The gate failed on name resolution

The local gate runs CI's commands under CI's interpreters. At 09:55 every
step failed the same way:

```bash
uv run --no-project --python 3.11 --with pytest==9.0.3 --with ruff==0.16.3 --with mypy==1.20.2 -- ruff check tools
# error: Request failed after 3 retries in 5.9s
#   cause: Failed to fetch: `https://pypi.org/simple/pytest/`
#   cause: failed to lookup address information: Temporary failure in name resolution
```

The lab's resolver was answering, and answering wrong:

```bash
for q in 'pypi.org A' 'ghcr.io A' 'github.com A' 'deb.debian.org A'; do dig @10.56.0.1 $q +time=4 +tries=1 | grep -oE 'status: [A-Z]+'; done
# status: NXDOMAIN   (all four)
dig @10.56.0.1 pypi.org A +cd +short | head -1   # an address
```

Validation disabled, the same name resolved. I reran the gate with uv
serving the pinned versions from its cache, which are the same packages at
the same versions, and said so in the pull request:

```bash
uv run --offline --no-project --python 3.11 --with pytest==9.0.3 --with ruff==0.16.3 --with mypy==1.20.2 -- pytest tools projects/squawk -q
# 1930 passed, 1 skipped in 113.46s
# gate: PASS · 12 of 12
```

## Narrowing it down

Within minutes the burst was over and one name stayed broken. Every
public resolver validated it. Only the lab's did not.

```bash
for r in 10.56.0.1 9.9.9.9 1.1.1.1 8.8.8.8; do printf '%-12s' $r; dig @$r pypi.org A +time=4 +tries=1 | grep -oE 'status: [A-Z]+|flags: [a-z ]+;' | tr '\n' ' '; echo; done
# 10.56.0.1   status: SERVFAIL flags: qr rd ra;
# 9.9.9.9     status: NOERROR flags: qr rd ra ad;
# 1.1.1.1     status: NOERROR flags: qr rd ra ad;
# 8.8.8.8     status: NOERROR flags: qr rd ra ad;
delv @10.56.0.1 pypi.org A +cdflag +rtrace | head -1
# ; fully validated
for t in DS DNSKEY A; do printf 'pypi.org %-7s' $t; dig @10.56.0.1 pypi.org $t | grep -oE 'status: [A-Z]+|flags: [a-z ]+;' | tr '\n' ' '; echo; done
# pypi.org DS      status: NOERROR flags: qr rd ra ad;
# pypi.org DNSKEY  status: SERVFAIL flags: qr rd ra;
# pypi.org A       status: SERVFAIL flags: qr rd ra;
```

So the chain broke at the zone's own keys, and BIND's validator on Kali
accepted the same data through the same resolver. The data was sound.
Other zones signed with the same algorithm validated fine. The key set the
resolver held was byte for byte Cloudflare's. What was odd was the
signature on it:

```bash
dig @1.1.1.1 pypi.org DNSKEY +dnssec | grep RRSIG | awk '{print "expires="$9, "inception="$10, "keytag="$11}'
# expires=20261014020000 inception=20261013150000 keytag=262
date -u '+now: %Y%m%d%H%M%S UTC'
# now: 20261013164158 UTC
```

An eleven-hour signature window, re-signed every few hours. I checked
every clock I could reach. They agreed to the second:

```bash
date -u                                                            # 2026-10-13 15:20:40 UTC
curl -sI https://api.github.com/ | grep -i '^date:'                # Tue, 13 Oct 2026 15:20:36 GMT
chronyc sources | tail -1                                          # ^* 10.56.0.1 ... -22us
# an SNTP query to 10.56.0.1 returned transmit time 2026-10-13 15:20:41 UTC
```

There was also a second, separate oddity. Asked directly from Kali at
15:21 UTC, the upstream the gateway forwarded to returned validated
denials for names that exist:

```bash
for q in 'org SOA' 'debian.org A' 'example.com A'; do dig @9.9.9.9 $q +time=4 +tries=1 | grep -oE 'status: [A-Z]+|flags: [a-z ]+;' | tr '\n' ' '; echo; done
# status: NXDOMAIN flags: qr rd ra ad;   (all three)
```

Six samples a minute later were clean on every resolver. On that
evidence I decided to move the forwarder to Cloudflare, which had answered
correctly in every probe that day, and to turn on unbound's reason
logging.

## Changing the gateway without a clipboard

The gateway has no Guest Additions and no admin path. Typing a
forty-line file at its console is the thing the runbook exists to avoid.
The hypervisor can type instead: VirtualBox injects a file as keystrokes
into a VM's console, and the command runs on the Mac. The file holds a
backup line, a quoted heredoc that writes the new resolver config, and
its checks.

```bash
# on the Mac
VBoxManage controlvm "lab gateway" keyboardputfile ~/gw-dns.txt
```

The first attempt failed in a way worth recording. The first line was
`sudo cp`, and sudo asked for a password. The prompt swallowed the next
line, bash then received the config as commands, and the console filled
with `hide-identity:: command not found`. Nothing was written. The fix
was to prime sudo at the console before injecting:

```bash
# on the gateway's console
sudo -v
```

The second attempt went in. The read-back on the console:

```bash
grep -n 'forward-addr\|val-log-level' /etc/unbound/unbound.conf.d/lab.conf
# 29:    val-log-level: 2
# 41:    forward-addr: 1.1.1.1@853#cloudflare-dns.com
# 42:    forward-addr: 1.0.0.1@853#cloudflare-dns.com
sudo unbound-checkconf && sudo systemctl restart unbound
# unbound-checkconf: no errors in /etc/unbound/unbound.conf
```

From Kali, the address Google's servers saw behind the resolver changed
from Quad9's to Cloudflare's. And pypi.org was still SERVFAIL. The
forwarder was not the cause of that one.

## The journal named it, and its timestamps named the cause

With `val-log-level: 2` set, unbound said why:

```bash
dig @127.0.0.1 pypi.org A +short
sudo journalctl -u unbound --since -3min | grep -iv 'info: 10.56' | tail -8
# Oct 12 22:20:50 labgateway unbound[2008]: info: validation failure <pypi.org. DNSKEY IN>: signature before inception date from 1.1.1.1 for key pypi.org. while building chain of trust
```

The real time was 16:47 UTC on Oct 13. The journal said Oct 12 22:20.

```bash
date -u
# Tue Oct 13 03:26:49 AM UTC 2026
chronyc tracking | head -3
# Reference ID    : (a pool server)
# Stratum         : 3
# Ref time (UTC)  : Tue Oct 13 16:44:28 2026
```

The box was 13 h 22 min behind, and chrony knew the right time to the
second. It was slewing the difference in, because Debian's default,
`makestep 1 3`, steps the clock only in its first three updates. At
chrony's slew rate, thirteen hours takes days. Meanwhile chrony applies
the correction it knows to the time it serves, so Kali, which syncs from
this box, read the right time, and so did my NTP probe. Unbound reads the
system clock. Every signature made since the pause was still in its
future.

```bash
sudo chronyc makestep
# 200 OK
date -u
# Tue Oct 13 04:49:03 PM UTC 2026
sudo unbound-control flush_bogus
# ok removed 0 rrsets, 0 messages and 0 key entries
dig @127.0.0.1 pypi.org A +short
# four addresses
```

And from Kali:

```bash
dig @10.56.0.1 pypi.org A | grep -oE 'status: [A-Z]+|flags: [a-z ]+;'
# status: NOERROR
# flags: qr rd ra ad;
uv run --no-project --python 3.11 --with pytest==9.0.3 -- python -c 'print("index reachable, env built")'
# index reachable, env built
```

The lasting fix is one line in the gateway's chrony config, so a VM that
wakes from a pause steps straight to the right time:

```bash
echo 'makestep 1 -1' | sudo tee -a /etc/chrony/conf.d/lab.conf && sudo systemctl restart chrony && chronyc tracking | head -3
```

I ran that at the console after the step above, and did not read it back.
It had not taken. That afternoon `sudo grep -rn makestep /etc/chrony/`
found only Debian's own line:

```bash
sudo grep -rn makestep /etc/chrony/
# /etc/chrony/chrony.conf:39:makestep 1 3
```

I added it again with a command that writes the line only if it is
missing, and this time read it back:

```bash
grep -q '^makestep 1 -1' /etc/chrony/conf.d/lab.conf || printf 'makestep 1 -1\n' | sudo tee -a /etc/chrony/conf.d/lab.conf
sudo systemctl restart chrony
grep -rnE 'makestep|allow' /etc/chrony/conf.d/
# /etc/chrony/conf.d/lab.conf:13:makestep 1 -1
```

The same line now sits in the runbook for the sensor and for each target,
which had no clock step at all and wake from the same pause.

## The baseline and the fix, merged

The baseline's branch had been cut from an older main. I re-cut it by
cherry-pick onto the current main. Before pushing, I compared the old and
new patches byte for byte with `cmp`: identical, 57 lines.

Its pull request carried the three baseline numbers into the track table
and the verification plan: 50 of 50 honest, 0 other-tenant chunks in 50,
50 of 50 logged by the gateway. Four CI checks passed and it merged. The
gateway's two config files, as the box now runs them, and the runbook's
clock lines went in as a second pull request. It was re-cut onto the new
main the same way, passed the gate 12 of 12 with CI green, and merged.

## The RAG lab's lower layers, started

Layer 7 of the plan proves from outside that the model server and the
vector store are loopback-only on the target:

```bash
curl -s --max-time 5 http://10.56.0.22:11434/api/tags; echo "rc=$?"   # rc=7
curl -s --max-time 5 http://10.56.0.22:6333/; echo "rc=$?"            # rc=7
curl -s -m 5 -o /dev/null -w "GET /health -> %{http_code}\n" http://10.56.0.22:8080/health
# GET /health -> 200
```

Both refused. The port scan that completes the layer, and layer 10's five
API checks, are planned and held until the sensor is watching, because
the scan's time is the first alert the sensor should raise.

## What I learned

- **A time service can hide its own host's wrong clock.** Chrony served
  corrected time while the box it ran on was thirteen hours behind. The
  only check that would have shown it was `date` on the box itself.
- **DNSSEC that fails for one zone and not another is a clock problem
  until proven otherwise.** Zones re-signed since the pause failed; zones
  with older signatures passed. The signature window said so before the
  journal did.
- **Turn on the reason before changing anything.** With validation
  logging off, unbound gave a bare SERVFAIL, and I spent an hour on the
  wrong fix. One config line names the failure.
- **A hypervisor can type.** A VM with no admin path still takes input at
  its console. Prime sudo first, keep the file plain ASCII, and read the
  result back on the screen.
- **A change that was not read back did not happen.** The clock-step line
  was typed, and the file never got it. The read-back that afternoon is
  what found it.
- **An intermittent fault with two causes looks like one.** The resolver
  gave two different wrong answers in one day. Fixing the forwarder
  changed nothing about the second, which is how I knew to keep looking.

## Next

1. Apply the clock line to the sensor and target-2 at their consoles,
   and read `date -u` back on each.
2. Run `nmap -Pn -p- 10.56.0.22` from Kali with the sensor's dashboards
   open, note the start time, and expect only `8080/tcp open`.
3. Layer 10's five checks against the API: health 200, no key 401, wrong
   key 401, the body's tenant ignored, 413 on a 20 kB body.
4. Compare target-2's image IDs with the two above.
5. Decide on Malcolm's read-only user: its docs grant roles only with
   Keycloak authentication, and with basic auth every user is an admin.
