# Kubernetes controls under GitOps, alerted on in the SIEM, and the Falco alerts that overwrote each other

| | |
| --- | --- |
| **Time** | About 1 hour on 31 October 2026 |
| **CISSP domains** | 7 Security Operations · 3 Security Architecture and Engineering · 5 Identity and Access Management · 6 Security Assessment and Testing |
| **Lab at the start** | The kind cluster from [the previous entry](2026-10-30-k8s-baseline-and-identity.md): API-server audit log on, OIDC identity from the identity provider, assessed with trivy, kube-bench and squawk. The security controls (NetworkPolicy, RBAC, Pod Security labels, an approved-registry admission policy) were applied by hand with `kubectl`. The audit log sat in a file inside the kind node, where nothing read it. |

The question: if someone changes a security control in the cluster, does the
change stick, and does anyone find out? At the start the answers were "yes" and
"only if they read a file on the node". One bug lost data quietly on the way,
and finding it took counting.

## Git as the source of truth

I put the controls in a git repository on a local Gitea server and installed
Flux 2.9.6 (`source-controller` and `kustomize-controller`). Flux pulls the
repository every minute and applies `clusters/lab/baseline` with prune on, so
anything removed from git is removed from the cluster too. Flux reads with a
token scoped to `read:repository`: a read returned 200, a write 403. The thing
that applies config to the cluster cannot change the config.

Then two changes of the same kind, made two ways. First the wrong way: I
deleted the namespace's default-deny NetworkPolicy with `kubectl`, which leaves
the namespace allow-all. Second, the right way: a commit that removed the client
allow rule from `kustomization.yaml`. The audit log, filtered to NetworkPolicy
writes in that namespace (times UTC):

```text
18:57:20  DELETE 200  deny-ingress-to-server   kubernetes-admin                                       | kubectl/v1.37.2
18:57:53  PATCH  201  deny-ingress-to-server   system:serviceaccount:flux-system:kustomize-controller | kustomize-controller/v0.0.0
19:00:19  DELETE 200  allow-client-to-server   system:serviceaccount:flux-system:kustomize-controller | kustomize-controller/v0.0.0
```

What to read: the user and the code. The hand delete is `kubernetes-admin`.
Flux put the policy back 33 seconds later. Server-side apply is always a PATCH,
so the code is what tells a restore from a routine check: `201` means Flux
created the object, `200` means it already matched. The third line is the git
change landing: Flux applied the new revision and prune deleted the rule. That
change has an author, a message, a diff and a `git revert`. The hand delete had
none of those, and it did not last.

## The audit log off the node

The audit log is root-owned, mode 600, inside the kind node. Fluent Bit on the
host runs as a systemd dynamic user and cannot read it. The API server's audit
webhook would need the node to reach a port on the host, and the host firewall
blocks that. So the shipper is a Fluent Bit DaemonSet on the control-plane
node, deployed by Flux, reading the file directly. It has no service-account
token and drops all capabilities. It runs as uid 0 only because the file is
`root:root 0600`, and root reads its own file without `CAP_DAC_OVERRIDE`.

The connection is mutual TLS, the same recipe as the host forwarders in earlier
entries: a key made on Kali and never moved, a certificate signed on the sensor
for `clientAuth` only, kept in a Secret that is never committed. The output
checks the authority and the sensor's name:

```text
host                  198.51.100.5
port                  5045
tls.verify            on
tls.verify_hostname   on
```

## Filtering at the edge

The audit log records every request: reads, leases, health probes. In a test
sample of 20,112 events, the filter shipped 386. It keeps completed writes
(`create`, `update`, `patch`, `delete`) to RBAC, NetworkPolicy, admission
policies and webhooks, namespaces, Secrets and service accounts. It drops two
kinds of Flux noise.

The first is Flux's once-a-minute check that changed nothing: a `PATCH 200` by
`kustomize-controller`. A Flux create or delete is kept, because that is the
revert half of a drift event.

The second I found in the first test, where every Flux event appeared twice.
Flux sends a dry run (`?dryRun=All`) before every real apply. The filter now
drops dry runs:

```lua
if string.find(r["requestURI"] or "", "dryRun=", 1, true) then return -1, ts, r end
```

This is a trade-off I chose and wrote down beside the code. An attacker can
dry-run a change to learn "would I be allowed?" without changing anything. That
is recon to hunt for in the raw log, not a change to page on.

Kept records are flattened into fields (`k8s_user`, `k8s_verb`, `k8s_code`,
`k8s_roleref`, `k8s_is_flux` and others), which land in Malcolm under
`miscbeat.*` with `event.module: k8s-audit`. I checked their types before
building any monitor: `k8s_user` text plus keyword, `k8s_is_flux` boolean,
`k8s_code` long. A field of the wrong type raises no error; the monitor never
fires.

## Monitors that name the identity

Two OpenSearch Alerting monitors, created in Dev Tools with
`POST _plugins/_alerting/monitors`. Both run every minute over the last five
minutes and are bucket-level monitors grouped by `miscbeat.k8s_user.keyword`.
Grouping by identity means each alert says who made the change, and two people
making changes raise two alerts instead of one count.

- `k8s-control-changed-outside-gitops` (severity 2): an RBAC, NetworkPolicy,
  admission-policy or webhook object written by anyone except Flux and the named
  control-plane housekeepers. A refused attempt (403) fires too.
- `k8s-cluster-admin-granted` (severity 1): any successful binding to
  `cluster-admin`, including one made by Flux. A reviewed grant of total control
  still deserves a page.

The housekeeping exclusions are listed by name:

```json
"must_not": [
  { "match": { "miscbeat.k8s_is_flux": true } },
  { "terms": { "miscbeat.k8s_user.keyword": [
      "system:apiserver",
      "system:kube-controller-manager",
      "system:serviceaccount:kube-system:clusterrole-aggregation-controller" ] } },
  { "prefix": { "miscbeat.k8s_user.keyword": "system:node:" } }
]
```

Excluding every `system:` user would have been shorter. It would also hide a
compromised service account, because service accounts are
`system:serviceaccount:…` too.

## The fire drill

I deleted the default-deny NetworkPolicy and bound `cluster-admin` to a new
binding, `drill-escalation`, both by hand. From the audit log (UTC):

```text
20:10:55  DELETE 200  networkpolicies     netpol-demo/deny-ingress-to-server | kubernetes-admin
20:11:04  CREATE 201  clusterrolebindings drill-escalation                   | kubernetes-admin  roleRef=cluster-admin
20:11:28  PATCH  201  networkpolicies     netpol-demo/deny-ingress-to-server | system:serviceaccount:flux-system:kustomize-controller
20:13:12  DELETE 200  clusterrolebindings drill-escalation                   | kubernetes-admin
```

In Malcolm, under Alerting → Alerts, both monitors were Active at 20:12 UTC,
each naming `kubernetes-admin`. Flux's restore at 20:11:28 raised nothing, which
is what I wanted: the revert is in the record, but nobody needs waking for it.
The last line is my clean-up. Change to alert took about a minute: Fluent Bit
flushes every 5 seconds, Malcolm ingested in about 11, the monitors run every
minute.

## Falco: what a container does once it runs

Admission and RBAC decide what may start, not what a running container does.
Falco 0.45.0 (chart 9.2.0, a pinned Flux `HelmRelease`) watches system calls with
the modern eBPF driver: no kernel module to build or load. It writes alerts as
JSON to a file on the node, the same shipper tails it into Malcolm as
`event.module: falco`, and a third monitor, `falco-runtime-alert`, fires one
alert per rule.

The first smoke test raised the alert I expected and two I did not (UTC):

```text
20:30:42.565Z Critical Drop and execute new binary in container  None/None          | mount -t tmpfs -o size=12869021696,noswap tmpfs /var/lib/kubelet/pods/
20:30:45.581Z Warning  Read sensitive file untrusted             default/falco-smoke | cat /etc/shadow
20:30:50.618Z Critical Drop and execute new binary in container  None/None          | umount /var/lib/kubelet/pods/4b10c5cf-…/volu
```

The two Critical alerts have no namespace and no pod (`None/None`). The
"container" was `lab-control-plane`, the kind node itself. In kind the kubelet
runs inside a container, so when it mounts a pod's token volume it looks like a
container running a binary that was not in its image. The exception, in git,
covers only that:

```yaml
- rule: Drop and execute new binary in container
  exceptions:
    - name: kind_kubelet_volume_mounts
      fields: [proc.exepath, proc.cmdline]
      comps: [in, contains]
      values:
        - [[/usr/bin/mount, /usr/bin/umount], /var/lib/kubelet/pods/]
  override:
    exceptions: append
```

Only `mount` and `umount`, only on the kubelet's pod-volume path. Any other
dropped binary in any container still fires. I did not key it on
`container.id`: that changes every time the cluster is rebuilt, and the
exception would stop matching without telling anyone. The same smoke test
afterwards gave exactly one alert, the real one.

Then the drill: `kubectl exec -it drill-shell -- sh`, then `cat /etc/shadow`.

```text
20:39:31.843Z Notice   Terminal shell in container    default/drill-shell | sh             | T1059,mitre_execution
20:39:48.862Z Warning  Read sensitive file untrusted  default/drill-shell | cat /etc/shadow | T1555,mitre_credential_access
```

Each alert names the namespace, pod and command, with its MITRE tag. At 20:40 UTC
`falco-runtime-alert` showed 2 Active alerts in Malcolm.

## Four alerts read, one arrived

After the shipper restarted, it read 4 Falco alerts from the file. Malcolm had 1.

I ruled things out in order. The shipper had read the whole file: its tail
offset equalled the file size. Nothing was stuck: the buffer was empty and the
log had no errors. Every hop reported success.

The answer was in Malcolm's source (v26.09.0). Each record gets a document ID
from a fingerprint stored in `event.hash`. Modules Malcolm knows get their own
fingerprint. Mine, `k8s-audit` and `falco`, fall to
`fingerprint_malcolm_beats_unknown` in `beats/98_finalize.conf`, which hashes
`host.name`, `event.module`, `event.dataset`, `agent.type`, `input.type` and
`@timestamp`. And `@timestamp` was the time Fluent Bit read the line. Four lines
read in one batch got one timestamp, so one ID, and each record overwrote the
one before. A forwarder cannot set `event.hash` itself: Malcolm lifts only
`host`, `agent`, `module` and `date` from what it receives.

The fix was to stamp each record with the time the event happened, taken from
the event itself. The audit parser reads `requestReceivedTimestamp`; the Falco
parser, `falco_json`, does the same with Falco's `time` field:

```text
[PARSER]
    name        audit_json
    format      json
    time_key    requestReceivedTimestamp
    time_format %Y-%m-%dT%H:%M:%S.%LZ
    time_keep   on
```

With a fresh tail position the file was read again from the top, and its six
alerts landed as six documents at their own event times. `@timestamp` now means
when it happened, which a SIEM timeline should show anyway. The risk left:
Malcolm parses `@timestamp` to the millisecond, so two events of one module in
the same millisecond can still collide. The proper fix is a Malcolm fingerprint
for these modules keyed on the audit ID, a change to the sensor's own pipeline
that I left for a session of its own.

## What I learned

- **The path decides whether a change sticks.** The hand delete and the git
  commit were the same kind of change. One was undone in 33 seconds; the other
  has an author, a diff and a revert. The audit log shows both, with the
  identity on every line.
- **Every filter rule is a decision about what not to see.** Dropping dry runs
  removed duplicate noise and also removed an attacker's "would I be allowed?"
  probe from the alert stream. I wrote that down next to the code, so the next
  reader knows where to hunt for it.
- **Name the exceptions.** Excluding all `system:` users was the short option,
  and it would have hidden service accounts, the identity an attacker in a pod
  holds. The Falco tuning names two binaries and one path, after reading which
  container fired showed the alerts came from kind's in-container kubelet.
- **A quiet SIEM is not a quiet cluster.** The pipeline reported success at
  every hop and still lost three of four records. Counting what arrived against
  what was sent was the only check that caught it.

## Next

The controls are in git, changes to them alert, and Falco watches running
containers. The blind spots, on record:

- **Who opened the shell.** Falco names the shell inside the container. The
  audit log, as configured here, does not record who ran `kubectl exec`. A
  later entry closes that gap.
- **No notification channel.** Alerts land in Alerting → Alerts, and one moves
  to Completed once its event is older than the five-minute look-back. Nothing
  yet sends an alert to a person or keeps a case history.
- **Same-millisecond collisions**, until Malcolm fingerprints these modules.

The managed equivalent on AKS is diagnostic settings streaming
`kube-audit-admin` to Log Analytics or an Event Hub, with the monitors written as
Microsoft Sentinel analytics rules, and the AKS GitOps extension running Flux.
