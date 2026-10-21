# 2026-10-13: The sensor was capturing, and its clock was twelve hours behind

| | |
| --- | --- |
| **Time** | About 1.5 h, between 10:00 and 12:45 CDT, alongside the [gateway entry](2026-10-13-gateway-clock-dns.md) |
| **CISSP domains** | 7 Security Operations · 4 Communication and Network Security · 6 Security Assessment and Testing · 3 Security Architecture and Engineering |
| **Lab at the start** | Gateway and Kali verified. Malcolm built on the sensor the day before. target-2 configured, and the RAG baseline run at 09:00 that morning, while the sensor was still down, so Malcolm has no record of it. |

## The goal

Bring the sensor back up and prove it sees the lab: a probe sent from Kali
has to show up in Malcolm, with the right source address and the right time.

## Malcolm does not start on its own

After I powered the sensor on, it answered ping, but its dashboards refused
connections:

```bash
nc -zv 198.51.100.5 443        # Connection refused
```

The cause is a default. Malcolm's configuration menu sets the container
restart policy to `no` (v26.09.0,
`scripts/installer/configs/configuration_items/docker.py`). The stack stays
down after a reboot until someone runs `./scripts/start`. After I started
it by hand, nginx answered at 11:47:51.

The fix is *Malcolm Restart Policy* → `unless-stopped` in
`./scripts/configure`. The check:

```bash
docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' $(docker ps -q) | sort | uniq -c   # only unless-stopped
```

## The probe arrived, filed under the night before

From Kali I sent two things across the gateway:

- a TCP SYN to the gateway's port 22
- a plain HTTP request to neverssl.com

The SYN gets no answer: the gateway's input chain drops it without a reset
and logs `nft in-drop`. It is still a good test. The SYN crosses Kali's
segment and is mirrored either way, and Zeek records it as an attempt with
no reply.

Malcolm showed three `conn` records to the gateway. The newest was dated
**Oct 12, 23:40**, the night before.

## Reading the sensor's clock without logging in

nginx puts its host's clock in the `Date:` header of every response,
including a 401. From Kali, with no credentials:

```bash
curl -sk -D - -o /dev/null https://198.51.100.5/ | grep -i '^date:'
```

At the same moment Kali read `16:57:47 GMT` and the sensor read
`04:49:02 GMT`. The sensor was **12 h 08 m 45 s slow**. Kali is a fair
reference: later that day `chronyc tracking` put its own clock 22 µs from
NTP time. Add that to the
"night before" record and it lands at 11:48:51 CDT, 40 seconds after the
probe left Kali. The capture was fine. The timestamps were wrong.

## Why the clocks were wrong

Two clocks were off that morning, for different reasons.

- **The gateway** was more than 13 hours behind, even though it had a
  working time source. Debian's chrony default, `makestep 1 3`, steps the
  clock only in its first three updates. After that it slews, and slewing
  in 13 hours takes days. The symptom was DNSSEC failures in unbound
  ("signature before inception date") on names that resolve fine.
  `chronyc makestep` fixed it on the spot, and `makestep 1 -1` makes the
  step permanent. That story is
  [its own entry](2026-10-13-gateway-clock-dns.md).
- **The sensor has no time source at all.** It sits on the management
  network only, and the lab's clock (chrony on the gateway) answers only
  the lab segments. Every Zeek, Suricata and Arkime record gets whatever
  time the VM woke up with.

A sensor that misfiles evidence looks healthy. The dashboards load, records
arrive, and nothing alerts. The only sign was a date that did not match.

## Fixing it

Today, by hand, from the measured offset. A relative step does not go stale
while you type it:

```bash
sudo date -s '+43725 seconds'
```

Measured again from Kali, the offset was **0 s**. Fresh traffic was then
indexed 4 to 15 seconds after it happened, at the right time: 190 records
from Kali in 15 minutes. Among them were Zeek `conn`, `dns` and `ssl`
records carrying the MAC addresses of Kali's lab NIC and the gateway's
`seg-kali` NIC.

The lasting fix gives the sensor the lab's clock without putting it on a
lab segment:

1. **One host route on the sensor:** `192.0.2.1/32 via 198.51.100.2`. The
   lab clock's address lives on the gateway's loopback.
2. **One input rule on the gateway**, admitting NTP from the sensor's
   address only. The packet is delivered locally, and nothing is forwarded
   between the management network and the lab:

   ```bash
   iifname "mgmt" ip saddr 198.51.100.5 ip daddr 192.0.2.1 udp dport 123 accept
   ```

3. **chrony on both ends.** The gateway gets `allow 198.51.100.5`. The
   sensor gets `server 192.0.2.1 iburst maxpoll 6` and `makestep 1 -1`.
   `maxpoll 6` caps the poll interval at 64 s, so after a pause about a
   minute of records at most carries the wrong time. The default ceiling
   is 17 minutes.

I tested the ruleset change before touching the live gateway. Kali parsed
and loaded it inside an unprivileged network namespace
(`unshare -rn nft -f nftables.conf`). That proves the syntax and the rule
order without affecting the host.

On the live gateway the rule goes in with `nft insert`, and the file is
edited separately. I did not reload the ruleset, because a reload resets
runtime sets to the file's defaults. Work on target-2 was going on at the
same time, and a reload would have closed any egress opened for it.

**Status at the end of the session:** the clock is stepped by hand. The
restart policy and the three-part fix are written and tested, and they get
applied next session, each with its check. The afternoon applied them and
put them through a pause and five reboots:
[the follow-up](2026-10-13-sensor-clock-proven.md).

## Reading what came back

With the clock right, I searched `source.ip:192.0.2.10` over the last 15
minutes and got 190 records. Each record has dozens of fields. These are
the ones that answered a question.

| Field | What to read in it |
| --- | --- |
| `source.ip`, `destination.ip`, `destination.port` | Who talked to whom, on what port. |
| `source.mac`, `destination.mac` | Where the frame was captured. Here `08:00:27:00:10:01` to `08:00:27:00:01:02`: Kali's lab NIC to the gateway's `seg-kali` NIC, on Kali's segment, before the gateway routed it. |
| `event.start`, `event.ingested` | When it happened by the sensor's clock, and when it was stored. Here 12:07:03.383 and 12:07:07.996. Seconds apart is the pipeline; hours apart is a clock. |
| `event.dataset` | Which Zeek log: `conn` is one record per connection, and `dns`, `ssl` and `http` add what was said in it. |
| `zeek.conn.conn_state` | How a connection ended. `S0` is a SYN with no answer, `REJ` a reset, `SF` a normal open and close. |
| `event.severity_tags` | Why Malcolm scored the record, in words, such as "Connection attempt, no reply". Read it before trusting `event.severity`. |
| `node` | Which sensor saw it. It matters once there is more than one. |

**Following one lookup to its connection.** The `dns` record for
`mobile.events.data.microsoft.com` (type `A`) and the `conn` record for
the same UDP exchange share `event.id` `CLRGrC4aFanfFQSQc84`. That is
Zeek's connection ID, and searching for it pulls every log line about that
one connection. `network.community_id` does the same job across tools.
Suricata computes the same value for the same flow, so it joins a Zeek
record to a Suricata alert.

**What I did not expect.** None of the first page was my test traffic. It
was Kali on its own: a lookup and a TLS session to
`mobile.events.data.microsoft.com`, a Microsoft telemetry endpoint and
probably the editor's, and a TLS session to `api.github.com`. For TLS the
server name (`related.hosts`) is the useful field, since the rest is
encrypted. That is the box's background, and it belongs in a baseline
before any test. Otherwise the first finding about the attack box is its
own editor.

**What I left alone.** `event.severity` and `event.risk_score_norm` read
20 on these records. They are Malcolm's own scores, built from rules like
the connection states above. Until there is a baseline they do not rank
anything.

## Two findings from Malcolm's source

I answered configuration questions from Malcolm's own source code
(v26.09.0), with file and line for each answer, rather than from memory or
forum posts. Two findings changed the design:

- **The syslog intake is open to the attack box.** Malcolm's Filebeat
  syslog listener accepts rsyslog's default framing. But it binds every
  address on the management network and has no authentication. Logstash
  also drops the sender's address. Kali is on that network, so it could
  write a line that reads exactly like the gateway's firewall log. Gateway
  log shipping stays off until the listener accepts only the gateway.
- **The tenant keys will be in the PCAP.** The RAG app takes its tenant
  from a bearer key sent over plain HTTP. Malcolm's Zeek logs HTTP header
  names, not their values, but Arkime keeps whole packets. The sensor's
  PCAP is a second place those keys live.

## What I learned

- **Monitoring needs monitoring of its own.** A sensor with a wrong clock
  produces records that look complete and are misfiled. What caught it was
  comparing two clocks, not reading a dashboard.
- **Time sync is part of evidence integrity.** A default that suits a
  physical server (`makestep 1 3`) leaves a paused VM hours wrong while its
  time service reports healthy.
- **Read the source behind a default.** The restart policy and the open
  syslog listener were both visible in Malcolm's code before either caused
  a gap.
- **A management network is still a network.** The sensor's dashboards and
  its syslog port can be reached from the box that runs the exploits.
  Anything that accepts input there needs a source restriction.

## Next

1. Apply the restart policy and the clock fix, each with its check.
2. Run the RAG baseline again with the sensor up: 10 questions, 5 trials
   each, 50 requests. The 09:00 run happened while Malcolm was down.
3. Count that run three times: the harness's count, the gateway's
   `nft scan-new` lines, and Malcolm's `conn`, `http` and Arkime records.
   All three should read 50, and Zeek's `capture_loss` should read 0. If
   the counts disagree, the gap says where to look.
