# 2026-10-13: The RAG baseline, counted three times

| | |
| --- | --- |
| **Time** | About 0.5 h, between 16:00 and 16:35 CDT |
| **CISSP domains** | 6 Security Assessment and Testing · 7 Security Operations · 4 Communication and Network Security |
| **Lab at the start** | The sensor's clock right from the first second after a boot ([that entry](2026-10-13-sensor-clock-proven.md)). target-2 configured, with its app on port 8080. |

## The goal

Every request the test harness sends to target-2 should be in Malcolm, and
that is to be counted, not assumed. The baseline is 10 questions asked 5
times each: 50 requests, one TCP connection each. The same 50 should show
up in three places:

- the harness's own CSV
- the gateway's firewall log
- Malcolm's Zeek records

## Two failed starts, and a health check that cannot fail

The first two runs stopped on their first request:

```bash
python3 -m harness run questions/honest.jsonl --trials 5 --url http://192.0.2.22:8080
# harness: POST http://192.0.2.22:8080/ask -> HTTP 502:
#   "ServiceError: POST http://127.0.0.1:11434/api/embed -> not reachable: Connection refused"
```

The app on target-2 was up, but the model server it calls on every
question (Ollama, on target-2's own loopback) was not. The app's health
endpoint said 200 the whole time, because it does not check anything:

```python
if self.path == "/health":
    self._send(200, {"ok": True, "tenant_filter": tenant_filter})
```

So "it's serving on 8080" was true and told me nothing about whether it
could answer. The only outside test of that is a real question.
`docker compose up -d` on target-2 started Ollama and Qdrant. The app,
which runs in the foreground on the same console, stopped while that was
typed, and had to be started again.

## The run

```text
start 2026-10-13 21:15:17 UTC
50/50 correct · http://192.0.2.22:8080
end   2026-10-13 21:15:48 UTC
```

There were 0 chunks from the other tenant in 50 answers, and 30.2 s of
model time in all, with the slowest answer at 5.8 s.

## Counted three times

| Count | Result |
| --- | --- |
| Harness | **50** rows in the CSV |
| Gateway, `nft scan-new` from Kali to 192.0.2.22:8080 | **50**, first at 16:15:17 CDT and last at 16:15:47 |
| Malcolm, Zeek `conn` | **50** |
| Malcolm, Zeek `http` | **50**, all `POST /ask` from `Python-urllib/3.14` |

The window matters. The counts above are for the run's exact window,
21:15:15 to 21:15:50 UTC. In the 15 minutes before it, the same
destination had 24 more new connections: the two failed attempts, one
refused run, and my own checks while the app was down. A count over "the
last 15 minutes" would have been wrong in a way that looks plausible. So
the gateway count uses absolute times:

```bash
sudo journalctl -k --since "2026-10-13 21:15:15 UTC" --until "2026-10-13 21:15:50 UTC" \
  | grep 'nft scan-new' | grep 'DST=192.0.2.22' | grep -c 'DPT=8080'
# 50
```

In Malcolm's Discover, set the same window as absolute dates, then run:

```text
destination.ip:192.0.2.22 and destination.port:8080 and event.dataset:conn    # 50
destination.ip:192.0.2.22 and destination.port:8080 and event.dataset:http    # 50
```

## What to read in the records

| Field | What it said here |
| --- | --- |
| `zeek.conn.conn_state` | `SF`, "Normal SYN/FIN completion", for all 50. The refused attempts were `REJ`. target-2's blocked DNS (below) was `S0`. Those three values sort a busy result list fast. |
| `user_agent.original` | `Python-urllib/3.14` is the harness. Three `curl/8.22.0` requests to `/health` at 16:25 were my clock checks, not test traffic. |
| `url.original` | `http://192.0.2.22:8080/ask`. Read this one, not `url.full`: Malcolm builds `url.full` as `http://192.0.2.22:8080:8080/ask`, with the port twice. |
| `source.mac`, `destination.mac` | Kali's lab NIC and the gateway's `seg-kali` NIC. Each packet is mirrored twice, once per segment it crosses, and Zeek still wrote one record per connection: 50, not 100. |
| `zeek.http.client_header_names` | Lists `AUTHORIZATION`. The tenant key's value is not in Zeek's records. |

## Two mistakes in the search box worth knowing

I was new to Malcolm's search that day. What I needed to know is in
[Searching Malcolm, for someone new to it](searching-malcolm.md).

- **Lucene treats a lowercase `and` as a word.** With the search bar in
  Lucene mode, `destination.ip:192.0.2.22 and destination.port:8080 and
  event.dataset:conn` matched any record with any of those terms: 546
  hits. In DQL the same text gave 50.
- **Arkime syntax typed into Discover still "works".** `ip.dst ==
  192.0.2.22 && port.dst == 8080` in Discover's DQL searched for the words
  and matched the 50 `http` records, whose `related.hosts` reads
  `192.0.2.22:8080`. The right number, for the wrong reason. Arkime's own
  count, from its own PCAP parsing, is done in Arkime.

## What the sensor found on the target

The Lucene mistake listed every connection in those 15 minutes. One of
them repeated every 5 seconds: target-2 sending DNS to `203.0.113.1`.
That is not a lab address. A search in DQL named what it was asking for:

```text
source.ip:192.0.2.22 and event.dataset:dns
# dns.host: 0.debian.pool.ntp.org, 1.debian.pool.ntp.org   (A and AAAA, every 5 s)
# destination.ip: 203.0.113.1   zeek.conn.conn_state: S0
```

target-2's time service was trying Debian's internet time servers through
a resolver left over from its install-time network. The gateway dropped
every query, correctly, so target-2 had no time source at all. Read from
Kali through the app's `Date:` header, target-2 was 12 to 13 seconds slow.
That would have put every line of its audit log 13 seconds off from
Malcolm and the gateway.

target-2 is on a lab segment, so it can reach the lab clock directly. The
fix was the sensor's timesyncd settings, plus the lab resolver:

```bash
printf '[Time]\nNTP=192.0.2.1\nFallbackNTP=\nPollIntervalMaxSec=64\n' | sudo tee /etc/systemd/timesyncd.conf.d/lab.conf
printf 'nameserver 192.0.2.1\n' | sudo tee /etc/resolv.conf
```

Measured from Kali afterwards: offset 0 s, three times in a row.

## One slip on the gateway

The count file started typing while `sudo -v` was still waiting for a
password. Three of its lines went in as password attempts, and the
gateway's auth log holds three failed sudo attempts at 16:18 CDT. This
entry is their explanation. After `sudo -v`, wait for the prompt to come
back before sending anything.

## What I learned

- **Count in a fixed window.** My own retries were real connections. A
  relative window would have folded them into the test.
- **A health check that cannot fail is not a check.** `/health` returned
  200 while the app could not answer a single question.
- **The query language is part of the query.** One mode turned "and" into
  a search word and gave a number ten times too large.
- **The sensor's first finding was about the lab, not an attack.** Before
  any attack test ran, it showed a target with no time source, asking for
  the internet every 5 seconds.

## Next

1. Arkime's own count of the run, from its PCAP, as a fourth record.
2. `capture_loss` for the run's window. It should read 0.
3. Reboot target-2 and prove its clock comes back on its own, as the
   sensor's now does.
4. The rest of the RAG lab's monitoring plan: a saved view per experiment,
   Suricata alerts on a port scan, alert rules, and retention sized to the
   sensor's disk.
