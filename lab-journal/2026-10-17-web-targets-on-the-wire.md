# A scanner found thirteen problems; the sensor raised thousands of alerts about something else

| | |
| --- | --- |
| **Time** | About 2 h on 17 October (the active scan ran for fifty minutes of it on its own) |
| **CISSP domains** | 6 Security Assessment and Testing · 7 Security Operations · 4 Communication and Network Security · 8 Software Development Security |
| **Lab at the start** | The RAG target and its monitoring were done ([Milestone 3](2026-10-14-milestone-3-baseline-monitored.md)), and the detections that watch the lab fire on real events ([Milestone 4](2026-10-16-milestone-4-detections.md)). One target segment was built, `seg-t2`, for the RAG app. No web targets. |

## What this milestone had to prove

A web application scanner and a network sensor watch the same attack and
count different things. The scanner reports what is wrong with the app. The
sensor reports what attack traffic crossed the wire. Before I could compare
them, I needed the target on its own segment, so every request was routed,
logged and mirrored, and I needed to know the two tools were seeing the same
traffic at all.

The vulnerable web applications are standard training targets — OWASP Juice
Shop, DVWA and VAmPI — run against a synthetic setup on an isolated lab
segment.

## The target, on the wire

The three web apps ran on Kali before this, bound to loopback. Traffic to a
loopback address never crosses a network interface, so no sensor could see
it. The point of this milestone was to move them.

They now run on `target-1`, a Debian VM alone on `seg-t1` (`192.0.2.18`),
from one Docker Compose file. DVWA gets the database it needs for its login
and injection pages. Each image is pinned by its multi-arch digest, and each
was checked for an arm64 build first: the older `vulnerables/web-dvwa` image
is amd64 only and will not run on this Apple-silicon host, so the check
chose `ghcr.io/digininja/dvwa`, which has an arm64 build.

The target has no route to the internet. Pulling the images needed a door
opened on the gateway for one address, for the length of the pull, and closed
in the same sitting.

## Seeing the same ten requests three ways

Before any attack, I sent ten ordinary requests to Juice Shop, each tagged in
its URL, and counted them in three independent places:

| Where | Count | What it is |
| --- | --- | --- |
| Gateway firewall log (`nft scan-new`) | 10 | the gateway recording each new connection before it forwards it |
| Zeek `conn`, on the mirror | 10 | the sensor seeing the same ten connections from outside |
| Zeek `http`, on the mirror | 10 | the ten requests, their tags intact |

The three agreed, and their last timestamps fell within two milliseconds of
each other across two machines' clocks — the clock work from an earlier
milestone holding up. With the counts proven on harmless traffic, a number
taken from the sensor later could be trusted.

## The scan, and the sensor

I ran an active scan from the scanner against Juice Shop: it crawled 920
URLs over about fifty minutes and sent real attack traffic — injection,
cross-site scripting, remote-file-include, path traversal. It found **13
high-severity** problems, 202 in all.

Over the same window, the network sensor's Suricata raised about **5,788
alerts** on that one target. Two tools, two numbers that look nothing alike,
both correct. The gap between them is the whole lesson, and it has two halves.

### Loud alarms for an attack that cannot land

Four rules fired 516 times each — about two thousand alerts — for PHP
attacks: `php://input` in a POST, `allow_url_include`, a generic PHP
remote-file-include, PHP tags in a request. Juice Shop runs on Node.js. It
has no PHP, so the scanner found no PHP problem at all. Suricata alerts on the
pattern in the request, not on whether it could ever work against this server.

For an analyst, that is the first triage move: knowing what runs on the asset.
Two thousand alerts for a PHP attack against a Node.js app are not two
thousand problems. They are noise to tune down for this target.

### The sensor's blind spot

Nine of the scanner's thirteen high findings were disclosures of fake personal
data — in a WebSocket stream, and in API responses. A search for any Suricata
alert about personal data over the scan window returned **zero**. A
signature sensor inspects requests for attack patterns; it has no rule for
"this response leaked personal data." The finding that matters most to a
privacy review is the one the network sensor cannot see. Those are caught by
the application's own logging, or a data-loss control, not by an IDS.

One detail worth reading closely: the alert URLs carried `%5B%24ne%5D`, which
decodes to `[$ne]` — a NoSQL operator, not SQL. Suricata labelled it "SQL
Injection." The attack class was right, the database was wrong. The rule name
is a starting point, not the verdict.

## An alert that was mine

Two alerts named an outside address in Canada as the source, answering a Kali
high port. An internet address talking to the attack box is worth a look. The
alert itself named the request: a `GET` for a `.deb` package from the Kali
mirror, with the package manager's user agent. Kali's own install log showed
the same two packages installed in the same minute the day before — the eBPF
tool from an earlier investigation. Benign, and a known change.

The triage used two witnesses that do not depend on each other: the network
alert, and the host's own install log. Each confirmed the other.

## Reading guide: what each output tells you

| Output | What it tells you |
| --- | --- |
| The scanner's high-finding count | what is wrong with the app it could reach — check the URL count, because a parameter the crawl never reached is untested, not clean |
| Suricata's alert count on one target | how much attack traffic crossed the wire, not how many problems exist |
| A rule firing the same count across several rules | one request shape that matches all of them, fired that many times — likely one test, not many |
| An alert whose source is the target | the server's response, flagged — the target is answering, not attacking |
| A zero on a category search (here, personal data) | what this kind of sensor cannot see, which tells you what other control you need |
| A `%`-encoded payload in the alert URL | the real attack, once decoded — `%5B%24ne%5D` is `[$ne]`, a NoSQL operator the rule called SQL |

## What I learned

- **An alert count is not a problem count.** The scanner found 13 real issues;
  the sensor raised thousands of alerts, most of them for an attack that could
  not work here. Counting alerts as problems would have buried the thirteen.
- **Know what runs on the asset before you triage.** PHP rules against a
  Node.js app are noise. The same alerts against a PHP app would be the
  opposite.
- **Two tools, two jobs.** The scanner measures application risk; the sensor
  measures attack traffic. Neither replaces the other, and the biggest findings
  here — personal data in responses — were visible only to the scanner.
- **Decode the payload before you trust the rule name.** The "SQL Injection"
  alerts carried a NoSQL operator.
- **Prove the instrument on harmless traffic first.** Ten tagged requests,
  counted three ways and agreeing, meant a later count off the sensor could be
  trusted. Checking that on an attack would have mixed two unknowns.

## Next

More web targets on the same VM, each checked for an arm64 build and pinned by
digest, and the same comparison for each: what the scanner finds against what
the sensor sees. Then back to the RAG track for Milestone 5.
