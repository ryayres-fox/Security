# Detection Engineering

Detections are treated as code: version-controlled, peer-reviewed, tested against sample data, and mapped to **MITRE ATT&CK**. Each use case documents intent, data source, logic, false-positive drivers, and response.

## Methodology

1. **Threat-informed** — pick techniques that matter for this environment (C2, exfil, discovery, lateral movement).
2. **Layered** — signatures (Suricata) catch known-bad; behavioral analytics (Zeek/DNS/flow) catch novel activity.
3. **Enriched** — GeoIP/ASN, threat-intel, and JA4 context are already on the event, so rules stay simple and fast.
4. **Measured** — track coverage, alert volume, and mean-time-to-detect; tune to keep signal high.

## Data sources

| Source | Provides |
|---|---|
| Zeek `conn.log` | Flow records: 5-tuple, bytes, duration, state |
| Zeek `dns.log` | Every query/response, per client |
| Zeek `ssl.log` / JA4 | TLS SNI, cert, client fingerprint |
| Suricata EVE | Signature alerts, protocol anomalies |
| Firewall logs | Pass/block decisions, NAT |

## Use-case catalog

| # | Use case | Signal | ATT&CK |
|---|---|---|---|
| 1 | C2 beaconing | Regular, low-jitter connections to one destination | T1071 / T1573 |
| 2 | DGA / suspicious DNS | High-entropy or long random domains | T1568.002 |
| 3 | Data exfiltration | Outbound bytes far exceeding baseline to a rare dest | T1041 / T1048 |
| 4 | Rare external destination | Device contacts an ASN/geo it never has before | T1071 |
| 5 | Internal scanning | One host touches many ports/hosts quickly | T1046 / T1018 |
| 6 | IoT policy violation | IoT device reaching outside its allowlist | T1071 |

Three are implemented below as samples.

---

## Sample 1 — C2 beaconing (analytic over Zeek `conn.log`, DuckDB SQL)

Beaconing shows up as many connections to one destination with **regular** inter-arrival times (low jitter). This flags src→dst pairs with tight timing regularity.

```sql
WITH deltas AS (
  SELECT id_orig_h AS src, id_resp_h AS dst, id_resp_p AS dport, ts,
         ts - LAG(ts) OVER (PARTITION BY id_orig_h, id_resp_h ORDER BY ts) AS gap
  FROM read_parquet('conn/*.parquet')
  WHERE ts > now() - INTERVAL 24 HOUR
)
SELECT src, dst, dport,
       COUNT(*)                         AS conns,
       ROUND(AVG(gap), 1)               AS avg_gap_s,
       ROUND(STDDEV_POP(gap), 1)        AS jitter_s,
       ROUND(STDDEV_POP(gap)/NULLIF(AVG(gap),0), 3) AS jitter_ratio
FROM deltas
WHERE gap IS NOT NULL
GROUP BY src, dst, dport
HAVING conns >= 20            -- persistent
   AND avg_gap_s BETWEEN 10 AND 3600
   AND jitter_ratio < 0.15    -- very regular = suspicious
ORDER BY jitter_ratio ASC, conns DESC;
```

**FP drivers:** software update pollers, NTP, telemetry. Tune with an allowlist of known-good destinations/ASNs (enrichment already provides ASN).

## Sample 2 — DGA / suspicious DNS (Sigma)

```yaml
title: Suspicious High-Entropy DNS Query (possible DGA)
status: experimental
description: Flags DNS queries with long, high-entropy labels characteristic of DGA C2.
logsource:
  product: zeek
  service: dns
detection:
  selection:
    query|re: '^[a-z0-9]{15,}\.'          # long random-looking leftmost label
  filter_known:
    query|contains:
      - 'amazonaws'
      - 'akamai'
      - 'windowsupdate'
      - 'googleusercontent'
  condition: selection and not filter_known
fields:
  - src_ip
  - query
  - answers
falsepositives:
  - CDNs and cloud hostnames with long random labels (partly filtered)
level: medium
tags:
  - attack.command_and_control
  - attack.t1568.002
```

Pair with an entropy calculation at ingest (Shannon entropy of the query) for a stronger score than regex alone.

## Sample 3 — Data exfiltration (rare destination + volume, SQL)

```sql
-- Outbound-heavy sessions to destinations this host rarely uses
WITH baseline AS (   -- destinations seen in the prior 30 days
  SELECT DISTINCT id_orig_h AS src, id_resp_h AS dst
  FROM read_parquet('conn/*.parquet')
  WHERE ts BETWEEN now() - INTERVAL 30 DAY AND now() - INTERVAL 1 DAY
)
SELECT c.id_orig_h AS src, c.id_resp_h AS dst, c.geo_dst, c.asn_dst,
       SUM(c.orig_bytes) AS out_bytes, SUM(c.resp_bytes) AS in_bytes,
       ROUND(SUM(c.orig_bytes)/1e6, 1) AS out_mb
FROM read_parquet('conn/*.parquet') c
LEFT JOIN baseline b
  ON c.id_orig_h = b.src AND c.id_resp_h = b.dst
WHERE c.ts > now() - INTERVAL 24 HOUR
  AND b.dst IS NULL                      -- never-before-seen destination
GROUP BY 1,2,3,4
HAVING out_bytes > 50e6                  -- >50 MB uploaded
   AND out_bytes > 5 * in_bytes          -- upload-dominant
ORDER BY out_bytes DESC;
```

## Sample 4 — Suricata signature (illustrative)

```
alert tls $HOME_NET any -> $EXTERNAL_NET any ( \
  msg:"POLICY Self-signed certificate to non-standard port"; \
  flow:established,to_server; \
  tls.cert_subject; content:!"CN="; \
  dsize:>0; \
  threshold:type limit, track by_src, count 1, seconds 300; \
  classtype:policy-violation; sid:9000001; rev:1; )
```

Managed rulesets (e.g., Emerging Threats Open) cover known-bad; custom SIDs like this encode local policy.

---

## Alerting & triage workflow

1. Detections write alerts to the store with severity + ATT&CK tags + enrichment already attached.
2. Dashboards surface **new/rare** activity and high-severity signatures first.
3. Triage: pivot from alert → the device's DNS + flow history → destination reputation (ASN/geo/intel) → decide (benign / tune / investigate / contain).
4. Containment for a home network = move the device to a quarantine VLAN and block egress at the firewall.

## ATT&CK coverage (sample)

| Tactic | Techniques covered |
|---|---|
| Command & Control | T1071, T1071.004 (DNS), T1573, T1568.002 (DGA) |
| Exfiltration | T1041, T1048 |
| Discovery | T1046, T1018 |

## Metrics tracked

- **Coverage:** techniques with ≥1 tested detection.
- **Signal quality:** alerts/day and true-positive rate per rule.
- **MTTD:** time from first malicious event to alert.
- **Rule health:** last-tested date; rules without recent validation get flagged.
