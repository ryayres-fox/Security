# Searching Malcolm, for someone new to it

I started using Malcolm on 2026-10-13. These are the things I needed to
know before a search returned the right number, in the order I needed
them. The examples are the lab's real searches from that day. The full
reference is Malcolm's own
[query cheat sheet](https://github.com/cisagov/Malcolm/blob/v26.09.0/docs/queries-cheat-sheet.md).

## 1. There are two places to search

- **Dashboards** (OpenSearch Dashboards). *Discover* is the page for
  searching single records. It holds Zeek logs and Suricata alerts.
- **Arkime**, linked from the Dashboards navigation as *Arkime*. It holds
  Arkime's own sessions, built from the full packet capture, as well as
  Zeek and Suricata.

They use different search syntax. A search written for one does not mean
the same thing in the other, and it can still return a plausible number.

## 2. Check the query language before every search

At the right end of Discover's search bar is a label: **DQL** or
**Lucene**. Click it to switch. Both are valid, and they read the same
text differently:

| You type | In DQL | In Lucene |
| --- | --- | --- |
| `a and b` | a and b | records with **a**, or **b**, or the word "and" |
| `a AND b` | a and b | a and b |
| `not a` | not a | records with the word "not", or **a** |

On 2026-10-13 the same search gave **546** hits in Lucene and **50** in
DQL, because Lucene read a lowercase `and` as a word. Pick DQL and write
operators in lower case, or pick Lucene and write them in capitals.

## 3. Set the time before the search

The time picker sits in the upper right. *Last 15 minutes* moves as you
watch. To count a test, open *Show dates* and set **absolute** start and
end times around it. The times are in your browser's time zone, not UTC.

## 4. The patterns that cover most searches (DQL)

| What | DQL | Example from the lab |
| --- | --- | --- |
| A field has a value | `field:value` | `destination.port:8080` |
| All of several | `and` | `destination.ip:192.0.2.22 and destination.port:8080` |
| Any of several | `or` | `zeek.conn.conn_state:REJ or zeek.conn.conn_state:S0` |
| Not | `not` | `not zeek.http.status_code:200` |
| A field exists | `field:*` | `zeek.http.status_code:*` |
| A subnet | quotes | `source.ip:"192.0.2.0/24"` |
| A wildcard | `*` | `dns.host:*pool.ntp.org` |
| Which log | `event.dataset:` | `event.dataset:conn`, `:http`, `:dns` |

Wrap parts of a longer search in parentheses so the order is not left to
chance.

## 5. The same field has two names

Dashboards uses the record's field names, and Arkime uses short aliases:

| Meaning | Dashboards (Discover) | Arkime |
| --- | --- | --- |
| Source address | `source.ip` | `ip.src` |
| Destination address | `destination.ip` | `ip.dst` |
| Destination port | `destination.port` | `port.dst` |
| Any address | `source.ip:X or destination.ip:X` | `ip == X` |

In Arkime, "and" is `&&` and "equals" is `==`:
`ip.dst == 192.0.2.22 && port.dst == 8080`. Typed into Discover, that
same text is read as a list of words. It matched 50 records that day,
because those records' `related.hosts` field held `192.0.2.22:8080`. So
the right number came back for the wrong reason.

## 6. Reading a result

- Click the arrow at the left of a row to open the record as a table of
  fields.
- In the field list on the left, add a few fields as columns. Fifty
  records become readable at a glance with `source.ip`, `destination.ip`,
  `destination.port`, `zeek.conn.conn_state` and `user_agent.original`.
- The fields that answered questions in this lab:

| Field | What it tells you |
| --- | --- |
| `event.dataset` | Which Zeek log: `conn` (one per connection), `dns`, `http`, `ssl`. Not `capture_loss` or `stats`: Malcolm files those in its runtime index, `malcolm_beats_*` (see section 7) |
| `zeek.conn.conn_state` | How a connection ended: `SF` normal, `REJ` refused, `S0` no answer |
| `event.id` | Zeek's connection ID. Search for it to get every log line about one connection |
| `network.community_id` | The same flow's ID across Zeek and Suricata |
| `user_agent.original` | Which program made an HTTP request. It told the test harness apart from my own checks |
| `url.original` | The URL as requested. `url.full` repeats the port in Malcolm (`:8080:8080`) |
| `source.mac`, `destination.mac` | Which segment the packet was captured on |
| `event.start`, `event.ingested` | When it happened, and when Malcolm stored it. Seconds apart is normal. Hours apart is a clock problem |

## 7. Before you trust a count

- **Absolute time window.** My own retries during the test were real
  connections, and a relative window counted them.
- **Language label checked.** DQL or Lucene, written to match.
- **Right tool.** Discover for Zeek and Suricata, Arkime for its sessions.
  Arkime's Sessions page lists Zeek's records too, since in Malcolm both
  live in one index. Add `&& event.provider == arkime` (the *Data Source*
  column) to count Arkime's own, and read the "of N entries" figure, not
  the page size.
- **One record opened.** Make sure the hits are the thing you meant, not
  something that shares a word with it.
- **Nothing dropped.** A count is only as good as the capture under it.
  Capture loss is not in Discover: open *Dashboards → Packet Capture
  Statistics* for the same window. Packets dropped should read 0 for
  Zeek and for Suricata. The two engines' packets-seen totals differ
  because they count differently, so compare the drops, not the totals.
  An empty dashboard is not a clean one: the numbers exist only when
  configure's *Gather Traffic Capture Statistics* is on.
