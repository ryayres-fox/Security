# Hunting Azure exposure with Resource Graph

Most of this repository shows AWS. This is the Azure counterpart, and it makes the
same argument the [open-source scanner estate](without-a-commercial-platform.md)
makes: you do not need a commercial CSPM to find your internet-exposed RDP port or
your unhealthy security assessments. Azure ships a free, agentless, read-only
query layer — **Azure Resource Graph (ARG)** — that answers those questions across
every subscription in one query, in seconds, without deploying a single collector.

ARG speaks **KQL** (the same query language as Log Analytics and Sentinel). It
indexes resource *properties*, not logs, so it is an inventory-and-configuration
hunting tool, not a SIEM. Everything below is written against the public ARG
schema and runs in the portal's Resource Graph Explorer, `az graph query`, or
`Search-AzGraph`.

A note on scope and freshness before the queries: ARG returns what your identity
can read, so run it high enough in the management-group tree to see everything you
own. And its index is *eventually consistent* — a resource changed seconds ago may
lag. It is the right tool for "what does my estate look like right now," not for
sub-second alerting.

---

## 1 · Find what's exposed to the internet

Start with the public IP addresses. The first question in any exposure review is
"what can the internet even reach?"

```kql
Resources
| where type == "microsoft.network/publicipaddresses"
| where isnotempty(properties.ipAddress)
| project name, location, subscriptionId, resourceGroup,
          ipAddress = tostring(properties.ipAddress)
```

A bare IP list is a start, but the useful question is *which machine* is behind
each address. Join public IPs → NICs → their private address and host, so a finding
names a VM you can act on rather than an orphan address:

```kql
Resources
| where type == "microsoft.network/publicipaddresses"
| where isnotempty(properties.ipAddress)
| extend nicId = tostring(properties.ipConfiguration.id)
| extend nicId = tostring(split(nicId, "/ipConfigurations/")[0])
| project publicIp = tostring(properties.ipAddress), subscriptionId, resourceGroup, nicId
| join kind=leftouter (
    Resources
    | where type == "microsoft.network/networkinterfaces"
    | mv-expand ipconfig = properties.ipConfigurations
    | project nicId = id,
              privateIp = tostring(ipconfig.properties.privateIPAddress),
              vmId = tostring(properties.virtualMachine.id)
  ) on nicId
| project subscriptionId, resourceGroup, publicIp, privateIp,
          vm = tostring(split(vmId, "/")[-1])
```

The join is the point: an exposed address you cannot tie to an owner is a finding
nobody will fix. Resolve it to a resource or the report is noise — the same rule
the [findings normalizer](../findings-normalizer/) enforces on every finding it
ingests.

## 2 · The headline finding — unrestricted management ports

The single most common serious misconfiguration in a cloud estate is SSH (22) or
RDP (3389) open to the whole internet. This query walks every network security
group, expands its rules, and returns only the inbound-allow rules that expose a
management port to `*` / `Internet` / `0.0.0.0/0`:

```kql
Resources
| where type =~ "microsoft.network/networksecuritygroups"
| mv-expand rule = properties.securityRules
| extend name        = tostring(rule.name),
         direction   = tostring(rule.properties.direction),
         access      = tostring(rule.properties.access),
         destPort    = tostring(rule.properties.destinationPortRange),
         srcPrefix   = tostring(rule.properties.sourceAddressPrefix)
| where direction == "Inbound" and access == "Allow"
| where srcPrefix in ("*", "Internet", "0.0.0.0/0")
| where destPort in ("22", "3389", "*")
| project subscriptionId, resourceGroup, nsg = name, ruleName = tostring(rule.name),
          destPort, srcPrefix
| sort by subscriptionId asc, nsg asc
```

Two things a shorter version of this query gets wrong, worth stating because they
cause silent misses:

- **A rule can hide the port in a range, not a single value.** `destinationPortRange`
  holds one value; `destinationPortRanges` (plural) holds an array like
  `["20-25", "3389"]`. A query that only reads the singular field misses `22`
  buried in a `20-25` range. A thorough sweep expands and checks both.
- **`*` is its own finding.** A rule with `destPort == "*"` exposes *every* port,
  which includes 22 and 3389. Filtering only for the literal strings `"22"` and
  `"3389"` would skip the worst rule in the estate — the one that opens everything.

That is why `"*"` is in the port filter above: the any-port rule is more dangerous
than the specific one, so it has to be caught, not filtered out.

## 3 · Misconfiguration — Defender for Cloud assessments

If Microsoft Defender for Cloud is on, its findings live in the `securityresources`
table as **assessments**. Every control it evaluates writes a Healthy / Unhealthy
row. Pull the unhealthy ones, newest severity first:

```kql
securityresources
| where type == "microsoft.security/assessments"
| extend status      = tostring(properties.status.code),
         displayName  = tostring(properties.displayName),
         severity     = tostring(properties.metadata.severity),
         resourceId   = tostring(properties.resourceDetails.Id)
| where status == "Unhealthy"
| project subscriptionId, resourceGroup, displayName, severity, resourceId
| sort by severity asc
```

For the detail behind a specific assessment — the individual vulnerable resources
and CVEs — join its **subassessments**. Filter to the one assessment you care about
by its `displayName` (a stable, readable string) rather than its GUID, so the query
stays legible and portable across tenants:

```kql
securityresources
| where type == "microsoft.security/assessments/subassessments"
| extend parent = tostring(split(id, "/assessments/")[1])
| extend parent = tostring(split(parent, "/")[0])
| extend displayName = tostring(properties.displayName),
         severity    = tostring(properties.status.severity),
         resourceId  = tostring(properties.resourceDetails.id),
         remediation = tostring(properties.remediation)
| project subscriptionId, resourceGroup, parent, displayName, severity,
          resourceId, remediation
```

This is the same pairing as [pslist vs psscan in memory forensics](memory-forensics.md):
the assessment tells you a control is unhealthy; the subassessment tells you
*which resources* and *what to do*. One is the alert, the other is the evidence you
act on.

## 4 · Catch drift — what changed, and when

Exposure is not static. A rule that was tight last week can be opened by a deploy
today. The `ResourceChanges` table records create/update/delete events, so you can
review everything that changed in a window — a lightweight, agentless audit trail:

```kql
ResourceChanges
| extend changeTime = todatetime(properties.changeAttributes.timestamp),
         changeType = tostring(properties.changeType),
         targetId   = tostring(properties.targetResourceId)
| where changeTime > ago(7d)
| project changeTime, changeType, targetId
| sort by changeTime desc
```

Scope it to the resource type that matters most for exposure — the network security
groups from section 2 — and drift review becomes a standing weekly check:

```kql
ResourceChanges
| extend changeTime  = todatetime(properties.changeAttributes.timestamp),
         changeType  = tostring(properties.changeType),
         targetId    = tostring(properties.targetResourceId)
| where changeTime > ago(7d)
| where targetId has "microsoft.network/networksecuritygroups"
| project changeTime, changeType, targetId
| sort by changeTime desc
```

Pair this with section 2 and you have the loop: section 2 tells you the estate is
clean *now*, section 4 tells you the moment that stops being true.

## Running it

| Where | How |
|---|---|
| Portal | Resource Graph Explorer — paste the query, pick the scope at the top |
| CLI | `az graph query -q "<KQL>"` (needs the `resource-graph` extension) |
| PowerShell | `Search-AzGraph -Query "<KQL>"` |

Run at the management-group scope, not a single subscription, or you only see part
of the estate — which reads as "clean" when it isn't. That partial-scope trap is
the [silent-failure pattern](silent-failure-patterns.md) in a hunting key: a query
that returned zero findings because it never looked at most of your resources is
indistinguishable from a query that returned zero because there was nothing to find.

---

*Azure Resource Graph is the agentless, no-cost hunting layer the
[commercial-platform comparison](without-a-commercial-platform.md) argues you can
build with. It finds the exposure; the discipline of turning each finding into an
owned, tracked, re-checkable record is the same one the rest of this repository is
built on. Every query here runs against the public ARG schema — no environment-specific
identifiers, no real subscriptions.*
