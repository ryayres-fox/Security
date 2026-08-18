# Reference Architecture

## 1. Objectives

Build a home/SOHO security monitoring platform that:

1. **Segments** the network so a compromised device (especially IoT) can't move laterally.
2. **Sees everything** that crosses zones or leaves the network, without sitting in the data path.
3. **Enriches telemetry in-stream** so stored records are analysis-ready.
4. **Detects** C2, exfiltration, scanning, and anomalous behavior with tunable, code-managed rules.
5. **Owns the data** — open formats, exportable logs, no closed appliance lock-in.

## 2. Threat model (abridged)

| Asset | Primary threats | Why it matters |
| --- | --- | --- |
| IoT / smart devices | Compromise → botnet, pivot, C2 | Weak firmware, rarely patched, chatty to the internet |
| Workstations / laptops | Credential theft, malware, data theft | Highest-value hosts |
| Network edge | Inbound exploitation, misconfig | Gateway is the trust boundary |
| Guest devices | Bringing in malware | Untrusted by definition |

Adversary behaviors of interest map to the Cyber Kill Chain and MITRE ATT&CK: **Command & Control (TA0011)**, **Exfiltration (TA0010)**, **Discovery (TA0007)**, **Lateral Movement (TA0008)**.

## 3. Design principles

- **Zero-trust segmentation** — every device on a VLAN matched to its role; default-deny between zones, explicit allows only.
- **Out-of-band monitoring** — the sensor receives a SPAN/mirror copy; it never adds latency or a failure point to live traffic.
- **Enrich before store** — GeoIP/ASN, threat-intel, and JA4/TLS context are applied as events flow, so hunts don't re-derive them.
- **Detection as code** — rules and analytics are version-controlled, reviewed, and tested like software.
- **Least privilege & isolation** — management interfaces live on a dedicated VLAN, never internet-facing.

## 4. Logical architecture

```
Internet ─▶ Firewall/Gateway (L3, zero-trust policy, DNS, IDS/IPS)
                 │ 802.1Q trunk
            Core Switch (VLANs + SPAN/mirror) ──▶ NSM Sensor
                 │                                   │
        ┌────────┼────────┐              Zeek + Suricata + DNS
     Wireless  Wired    Servers            │  (Layer-1 enrichment:
     (per-SSID  VLANs                      │   Intel, GeoIP/ASN, JA4)
      → VLAN)                              ▼
                                   Enrichment pipeline (Layer-2:
                                   threat-intel join, DNS↔flow,
                                   schema normalize)
                                              ▼
                                   Search + dashboards (SIEM)
                                              ▼
                                   Detections → alerts → analyst
```

See `network-diagram.svg` for the rendered version.

## 5. Network segmentation

Default-deny between zones; inter-zone flows are allowlisted per requirement.

| VLAN | Zone | Egress policy |
| --- | --- | --- |
| 10 | Trusted (workstations) | Broad internet; management access to infra by rule |
| 20 | Guest | Internet only; isolated from all internal zones |
| 30 | IoT | Internet-restricted / allowlisted; forced internal DNS; no lateral |
| 40 | AV / Media | Internet + scoped mDNS reflection from Trusted only |
| 50 | Servers / Lab | Explicit rules per service |
| 90 | Management | Admin host(s) only; no internet where possible |

## 6. Monitoring data pipeline

1. **Capture** — Core switch mirrors inter-VLAN + uplink traffic to the sensor's monitor NIC.
2. **Analyze (Layer-1 enrichment at capture)** — **Zeek** produces protocol logs (conn, dns, x509, files, http) and applies its Intel Framework, GeoIP/ASN, and JA4 fingerprints inline; **Suricata** runs signature detection (EVE JSON) with managed rulesets.
3. **Enrich (Layer-2, in-stream)** — a streaming processor joins threat-intel, correlates DNS→flow, normalizes schema, and writes **already-enriched** records.
4. **Store & search** — enriched metadata lands in an indexed store (e.g., OpenSearch) and/or columnar files (Parquet/DuckDB) with tiered retention.
5. **Detect & alert** — behavioral analytics + signatures generate alerts; see `detection-engineering.md`.

## 7. Example implementation stack

Vendor-neutral by design; a concrete reference build:

- **Gateway/firewall:** OPNsense (open, scriptable, NetFlow/syslog export, inline Suricata).
- **Switch:** any L2+ managed switch with 802.1Q + port mirroring.
- **Sensor:** small fanless x86 appliance running Zeek + Suricata.
- **Pipeline/store:** Malcolm (CISA) — bundles Zeek/Suricata/OpenSearch — or a Vector/Logstash → OpenSearch/DuckDB pipeline.
- **Enrichment data:** MaxMind GeoIP/ASN, an IOC/domain feed, JA4 databases.

## 8. Data retention & sizing

Metadata (Zeek/Suricata/DNS) is **orders of magnitude smaller** than full packet capture — typically GB/day for a home network vs. TB/day for PCAP — so months-to-years of searchable history is practical on a single NVMe. Full packet capture is an optional add-on with short, rolling retention when deep forensics justify the storage.

## 9. Scope & assumptions

- Encrypted traffic is **not** decrypted; visibility comes from metadata (SNI, JA4, DNS, cert, flow shape) — no endpoint certificates or MITM required.
- Single-site, single-analyst operation; scales by adding sensors or a message bus (Kafka) if needed.
