# Milestone 4: detections that fire on real events, and the ones that failed quietly first

| | |
| --- | --- |
| **Time** | About 12 h, estimated from the session's timestamps: 4 h on 14 October, 6 h on 15 October, 2 h on 16 October |
| **CISSP domains** | 7 Security Operations · 6 Security Assessment and Testing · 4 Communication and Network Security · 5 Identity and Access Management · 2 Asset Security · 3 Security Architecture and Engineering |
| **Lab at the start** | The RAG baseline counted four ways, every box keeping one clock across a power cycle ([that entry](2026-10-14-milestone-3-baseline-monitored.md)). Malcolm saw the mirrored traffic; nothing else reached it. No alert rules. Kali had no firewall of its own. |

## What this milestone had to prove

A detection counts as done when it has fired on a real lab event, not when
it is configured. Before any alert could mean something, two other things
had to hold: the logs reaching Malcolm come only from the machines that
should send them, and they carry the right time. And the data has to stay
long enough to be searched, readable by someone who cannot change it.

Most of what follows is about the detections that looked fine and were not.

## Kali gets its own firewall

The case that started this: a Python web server left running on Kali
served the Mac for over an hour on the management network, and no log
anywhere recorded it. The gateway logs what crosses it; this never did.

Kali now has an nftables table of its own. Every new inbound connection is
dropped and logged (`kali mgmt-drop`, `kali lab-drop`), unless its port is
in a set I open on purpose, with a timeout:

```text
sudo nft add element inet kali mgmt_open '{ 8765 timeout 20m }'
```

Two details took longer than the rules:

- **Docker owns other tables on the same box.** Debian's nftables service
  flushes the whole ruleset when it stops, which would wipe Docker's rules
  too. Kali's file adds and deletes only its own table, and the service's
  stop step deletes only that table.
- **Broadcasts drowned the log.** 236 of the first 241 drops were the Mac
  and other hosts announcing themselves. Broadcast and multicast are now
  counted and dropped without a log line.

The same Mac request now times out, and Kali logs it.

## Logs into Malcolm, and who may send them

Kali's kernel log, where its firewall writes, goes to Malcolm through
Fluent Bit over TLS to Malcolm's Filebeat listener (port 5045), with a
client certificate of Kali's own. The key was made on Kali and never left
it; only the signing request and the signed certificate crossed the
network. Malcolm cannot search inside a forwarded line (it keeps the line
in `event.original`, mapped as not indexed), so Fluent Bit splits each
firewall line into fields first: `nft_prefix`, `nft_src`, `nft_dst`,
`nft_dpt` and the rest.

**My reading of the configuration was wrong.** Malcolm's Filebeat file says
`ssl.verification_mode: "none"`, and I predicted it would take a client
certificate from anyone. The test said otherwise:

```text
openssl s_client -connect 192.168.56.5:5045 -tls1_2
  no client certificate      → alert handshake failure (40)
  a self-signed certificate  → alert unknown ca (48)
```

Only a certificate signed by Malcolm's CA gets in. I recorded the test, not
my prediction.

The gateway's firewall log followed the next morning, by the same chain
with a certificate of its own. The sensor cannot reach into the gateway, so
the gateway pushed its signing request to a one-shot listener on the
sensor that took connections from the gateway's address only. It refused a
test from Kali first.

## The scan Suricata did not see

A full `nmap -p-` of the RAG target raised no Suricata alert at all.
Suricata's scan rules look for traffic from outside the home network, and
Malcolm's default `HOME_NET` is all private address space, so Kali counted
as an insider. `HOME_NET` is now only the target segments, `10.56.0.16/29`.

Checking the change caught a second mistake. Suricata's container rewrites
its configuration at every start and leaves a backup each time, and my
first read-back read one of the ten backups. Reading the live file:

```text
HOME_NET: 10.56.0.16/29
EXTERNAL_NET: '!$HOME_NET'
```

The same scan then raised 7 alerts from 5 rules: probes to the Oracle,
MySQL, MSSQL, PostgreSQL and VNC ports.

## Alerts, each one fired on purpose

Each alert is an OpenSearch Alerting monitor that checks every 5 minutes
over the last 10. Each was proven by making the event happen:

| Monitor | Fires on | Proven by |
| --- | --- | --- |
| Kali: new inbound on mgmt | any `kali mgmt-drop` | a `curl` from the Mac to a closed port |
| Zeek: scan notice | a Zeek notice of category `Scan` | `nmap` against the target |
| Suricata: alert against a target | any alert whose destination is a target segment | the same scan |
| target-2: a new service | a connection to the target answered on any port but the app's | a test listener on port 9999, reached from Kali |
| Gateway: link-local request | anything sent to `169.254.0.0/16` | a `curl` to the metadata address |
| Gateway: a target tried to leave | a `fwd-drop` whose way in is a target segment | the target trying to reach the internet |

**The Zeek monitor stayed silent through a scan Zeek did flag.** It
filtered on `zeek.notice.category`, which exists in Zeek's own logs but
not in Malcolm's: Malcolm files a notice's category and name under
`rule.category` and `rule.name`. Fixed, it fired on the next scan. Since
then I confirm a field with a search before building a rule on it.

**The new-service monitor must not fire on a scan.** A scan's probes to
closed ports end `REJ`, and the only open port is the app's. So its proof
had to be the opposite case: something new listening. A 10-minute
`python3 -m http.server 9999` on the target, two requests from Kali, and
the alert two minutes later.

**The target cannot leave the lab.** From the target, `curl` to
`https://example.com` and to `https://1.1.1.1` both timed out, and Malcolm
holds the gateway's `nft fwd-drop` lines for every attempt, to both of
example.com's addresses and to 1.1.1.1. The last monitor in the table
fired on them.

## Retention, and the data I deleted

Malcolm deletes its oldest indices once they pass a size limit, and Arkime
deletes its oldest packet capture when the disk runs low. I set the index
limit to 60, meaning 60 GB, through Malcolm's configure menu. In Malcolm's
pruning script, a value of only digits is **megabytes**:

```text
if args.limit.isdigit():
    return int(args.limit)          # megabytes
```

At its next scheduled run, 09:20 CDT on 15 October, it deleted 16
indices, about 393 MB: every network index from the first capture to that
morning, and most of the forwarded logs. I had read the value back after the restart, not
before. The same trap sat in the next setting: Arkime reads a bare `20` as
20 GB of free space, and `20%` as a percentage.

**The packet capture had not been touched, so I rebuilt from it.** Three
things in Malcolm's source shaped how:

- **The file dates were no guide.** Malcolm touches every capture file it
  watches each time it starts, so after a restart every file looked new.
  The file names carry their start time in seconds, so I chose files by
  name.
- **Malcolm skips a file it has seen**, by name and size, so it would have
  ignored the old files. I fed it copies under a new name, which also
  tagged every rebuilt record `rebuild`.
- **One file first**, checked, then the other 134.

The proof was a count taken before the loss. The baseline run from 13
October, counted again in the rebuilt data, gave the same 50 Zeek
connections, 50 HTTP records and 50 Arkime sessions. The rebuilt data is
not identical to the original, and it is labeled: Suricata re-read the old
scans with the corrected `HOME_NET` and now raises alerts on them that the
live sensor missed at the time. Some things did not come back: the
forwarded logs, which are not in packet capture, and a few minutes at the
edge of the deletion.

Both limits are now written with their units, `60G` and `20%`, read back
before every restart, and read again from the running containers after.

## The alert that went silent

The Kali monitor had last fired on 14 October. On 15 October, checking a
saved search, I saw the newest Kali firewall record was from early
morning, though I had made connections minutes before. Kali's own journal
had the same connections almost 12 hours later than Malcolm's copies:

| Event | Kali's journal | Malcolm |
| --- | --- | --- |
| Mac → Kali:8765, source port 61918 | 17:19:28 | 05:36:38 |
| Mac → Kali:8765, source port 62045 | 17:32:50 | 05:50:01 |

Fluent Bit's kernel-log input dates each line from the kernel's uptime, and
uptime stops while the VM is paused. The host laptop sleeps, so every
pause pushed new records further into the past. The alert looks back 10
minutes and never saw them. It had been silent for a day, and it looked
healthy the whole time.

Fluent Bit now reads the kernel's lines from the systemd journal, which
stamps each one with the clock time it was written, with the record kept
exactly as before so the monitors needed no change. I tested the new
input by hand before installing it. A test connection then landed in
Malcolm at the same milliseconds as in Kali's journal, and the Kali alert
fired again within five minutes. On the gateway the change also removed a
privilege: reading `/dev/kmsg` there needed `CAP_SYSLOG`, and reading the
journal does not.

## A login that can only read

With Malcolm's basic login, every account is an administrator; Malcolm's
own documentation says so. A read-only user needs roles, and roles need
Keycloak, which Malcolm ships as its own container. The switch took three
traps, each traced to Malcolm's source:

- **The database password that never changes.** Keycloak's database user
  is created at Malcolm's first start and keeps that password. Malcolm's
  setup tool offered to regenerate it, which changed only the settings
  file. Keycloak then waited forever at "PostgreSQL is responding": its
  start-up check sends its errors to `/dev/null`. Only the database's own
  log said `password authentication failed for user "keycloak"`, every 5
  seconds. Putting the original password back fixed it.
- **A stale address.** nginx looks up Keycloak's container address when
  nginx starts. Keycloak was re-created twice, nginx kept the old address,
  and the login page was a 502 until nginx restarted too.
- **A secret nobody had to see.** The client secret Malcolm needs from
  Keycloak was read by Keycloak's own admin tool inside its container and
  written to Malcolm's settings, never typed or displayed.

The proof is in nginx's access log. The read-only user opened a saved
search, then tried to save one:

```text
"POST /dashboards/api/saved_objects/search?overwrite=true HTTP/1.1" 403
```

Not yet run: the same save as an administrator, which should give 200 and
would show the refusal comes from the role.

## Who kept asking the metadata address

`169.254.169.254` is where a cloud VM's software asks for its credentials
and its identity. Kali is not a cloud VM, and kept asking.

**The first source was my own test suite.** Malcolm showed 1,052
connections from Kali to that address in one day, in bursts that lined up
with test runs. A logging wrapper placed ahead of the real AWS command-line
tool showed the unit tests calling it 15 times per run, and with no
credentials configured, that tool asks the metadata address first. On a
machine with real credentials, the same tests would have called real AWS.
The suite now runs against a fake AWS tool, with tests that fail if the
real one is ever called; two full runs made 0 real calls and Malcolm saw 0
metadata connections during them.

**The bursts kept coming with no test running.** The firewalls log the
port, not the program, so I put an eBPF probe on Kali: bpftrace on the
kernel's `tcp_connect()`, printing the process, its user and its parent
for that one destination. It caught VS Code's extension host, the single
process where every extension runs. Three installed extensions bundle
Microsoft's Application Insights telemetry library, and its "Statsbeat", a
report on the library itself every 15 minutes, asks the address whether it
runs on an Azure VM. On one it would report the VM's ID and subscription.
Here the request fails, the answer stays unset, and it asks again every
cycle: 09:54:53, then 10:09:53.

**My first fix was wrong.** I read the extensions' telemetry code, saw that
it builds its sender only when VS Code's telemetry is on, and turned
telemetry off. After VS Code restarted, the probe caught the new process
asking again, 15 minutes later. Whatever that setting stops, it does not
reach Statsbeat. Statsbeat has its own switch, an environment variable every
copy of the library reads, `APPLICATION_INSIGHTS_NO_STATSBEAT`. It is now
set at login, so VS Code has it before any extension starts. One of VS
Code's built-in extensions sets the same variable, but only when it loads,
after other extensions have already read it.

With the variable set at login, VS Code ran from 11:05 to 12:25 and the
probe saw no request to the address: four 15-minute beats came and went in
silence. Checking that the variable reached VS Code needed one more lesson.
VS Code is built on Chromium, which writes its process titles over
`/proc/<pid>/environ`, so reading a `code` process there shows nothing
either way. VS Code's own terminal is the honest witness: its shell is
started by VS Code's main process, with the environment the extension host
gets, and it read `APPLICATION_INSIGHTS_NO_STATSBEAT=1`.

## What to read in the output

| Output | What it tells you |
| --- | --- |
| A firewall line's prefix (`kali mgmt-drop`, `nft fwd-drop`) | which rule saw the packet, and so what kind of event it was |
| `openssl s_client` alerts 40 and 48 | 40: no client certificate; 48: a certificate the server's CA did not sign |
| Suricata's live `HOME_NET` | who counts as an outsider, which decides whether scan rules fire at all |
| A record's `@timestamp` next to the source's own log | whether the time survived the trip; a fixed offset means a clock problem, not a delay |
| `nginx` access log status codes | 403 is a role refusing; 502 is nginx unable to reach what it fronts |
| The probe's `comm`, `pid` and parent | which program opened the connection, which a firewall line cannot tell |

## What I learned

- **A detection is done when it fires.** Three of them looked configured
  and could not have fired: the scan rules because of `HOME_NET`, the Zeek
  monitor because of a field name, the Kali alert because of a clock.
- **Test the prediction, not the reading.** I was wrong about who Malcolm
  would let in, and wrong about which switch stops the telemetry. Both
  times the test was minutes; believing the reading would have been
  permanent.
- **A bare number is a unit someone else chose.** The deletion came from a
  `60` that meant megabytes. Every limit is now written with its unit and
  read back before it can act.
- **A log's time is evidence.** Uptime counts how long a machine has run;
  only the clock says when something happened. Mixing them made an alert
  look healthy while it saw nothing.
- **Monitor for silence too.** Nothing told me the Kali alert expected
  traffic. At a larger scale, an alert on a source going quiet would have
  caught it the same hour.
- **Keep recovery paths separate.** The packet capture had its own
  retention, and that is the only reason the deletion was recoverable. A
  snapshot of the indices before the change would have made it a restore.

## Next

Milestone 5: attacking the RAG app against the OWASP Top 10 for LLM
Applications, starting with indirect prompt injection. Before that, two
more checks on the target: the containers' image IDs and users, and the
vector store refusing a request without its key. Each experiment is
measured twice, for what it stops and for what it costs on the honest
questions, with Malcolm counting every request.
