# A cluster with its audit log on, assessed three ways, and my own controls in the findings

| | |
| --- | --- |
| **Time** | About 1 hour on 30 October 2026 |
| **CISSP domains** | 6 Security Assessment and Testing · 5 Identity and Access Management · 7 Security Operations · 3 Security Architecture and Engineering |
| **Lab at the start** | A single-node `kind` cluster on the Kali workstation, plus the existing Malcolm sensor and a Keycloak identity provider already in the lab. Nothing hardened yet. |

The first entry in a new track, a Kubernetes security lab built from the
public Kubernetes documentation. The goal was a baseline I could trust: a
cluster that records every change, a few first controls, an assessment that
finds what is missing, and users who log in through an identity provider.

## A cluster that records changes from the first minute

Kubernetes keeps no audit trail unless you ask for one. The API server is the
one door every change passes through, so that is where the record has to be
made. `kind` lets you patch the API server's flags at creation, so I turned
the audit log on before the cluster existed:

```yaml
apiServer:
  extraArgs:
    audit-policy-file: /etc/kubernetes/audit/policy.yaml
    audit-log-path: /var/log/kubernetes/audit/audit.log
    audit-log-maxage: "7"
    audit-log-maxbackup: "3"
```

```
kind create cluster --name lab --config kind-config.yaml
kubectl get nodes
```

The audit policy decides what gets written. I wrote it around changes, not
reads ([audit policy reference](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)):

| Rule | Level | Why |
| --- | --- | --- |
| `get`, `list`, `watch` | None | read-only calls are noise for change auditing |
| Roles, ClusterRoles and their bindings | RequestResponse | who, and the exact rule they granted |
| NetworkPolicies | Request | the rule added or removed |
| Secrets, ConfigMaps | Metadata | that it changed, never the value |
| Pod create and delete | Request | catches a privileged pod being launched |
| any other write | Metadata | who, what, when |

Keeping secrets at `Metadata` is the line I cared most about. An audit log
that stores secret values becomes the most valuable file on the cluster.

## First controls, then an escalation on purpose

Before assessing anything I put in the controls an assessment should look
for, each in its own namespace:

- a least-privilege Role in `dev`: a service account that may `get`, `list`
  and `watch` pods in that namespace and nothing else
- a default-deny ingress NetworkPolicy in `netpol-demo`, then one allow rule
  from `app=client` to `app=server`
- a namespace at the `restricted` Pod Security level, and a pod built to
  meet it: non-root, no privilege escalation, every capability dropped, the
  default seccomp profile
- a ValidatingAdmissionPolicy, written in CEL, that only admits images from
  `docker.io` or `registry.k8s.io`. Pod Security cannot express a rule about
  registries; this is the built-in way to add one.

I checked the Role with `kubectl auth can-i --as=` against the service
account. It could read pods in `dev`, and nothing else, anywhere else.

Then I did the thing the audit log exists to catch. I bound `cluster-admin`
to a service account, a deliberate privilege escalation, and went looking for
it in the audit file on the control-plane node. The entry was there, at
`RequestResponse` level, so it carried the whole story in its fields:

| Field | What it answered |
| --- | --- |
| `user.username` | who made the grant |
| `verb`, `objectRef.resource` | `create` on `clusterrolebindings` |
| `requestObject.roleRef.name` | `cluster-admin`, the role granted |
| `requestObject.subjects` | the service account that received it |
| `requestReceivedTimestamp` | when |

I deleted the binding, and the delete was in the trail as well. That one line
is what an alert for this escalation should contain. Nothing reads the file
yet except me, which is the gap the next entry closes.

## Assessment one: trivy, and the policy that blocked it

The controls above each close one gap I knew to look for. The harder question
is a cluster I did not build: how do I find every workload missing those
controls? The answer is to scan the running cluster against a known baseline
and let the tool list the gaps. I started with
[trivy](https://trivy.dev/)'s cluster scan.

The first run failed:

```
FATAL ... pods "node-collector-..." is forbidden: ValidatingAdmissionPolicy
'require-approved-registry' ... denied request: image must come from an approved
registry (docker.io or registry.k8s.io)
```

My own registry policy had blocked the scanner. trivy starts a
`node-collector` pod to read node files, and that image comes from `ghcr.io`.
The policy applies to the whole cluster, so it refused a tool I wanted.

Weakening the policy was the wrong fix. The options were scoped exceptions:
exclude a tooling namespace on the policy's binding, allow the scanner's
registry path, or skip the node collector for this run. I skipped it and got
the node checks from kube-bench instead. Any exception is a change to a
restriction, so it belongs on the same reviewed, audited path as any other
policy change.

```
trivy k8s --disable-node-collector --report summary --scanners misconfig
```

The workload part of the summary:

```
│ secure             │ Pod/hardened                      │   │ 1 │ 2 │ 6  │   │
│ netpol-demo        │ Pod/client                        │   │ 3 │ 5 │ 10 │   │
│ netpol-demo        │ Pod/server                        │   │ 3 │ 5 │ 10 │   │
│ local-path-storage │ Deployment/local-path-provisioner │   │ 3 │ 4 │ 10 │   │
│ dev                │ Pod/intruder                      │   │ 3 │ 5 │ 10 │   │
│ default            │ Deployment/demo-app               │   │ 3 │ 3 │ 11 │   │
│ default            │ Pod/okreg                         │   │ 3 │ 4 │ 11 │   │
```

The columns are Critical, High, Medium, Low, Unknown. The column to read is
High. The hardened pod has 1 High where every other workload has 3, and the
Highs on the others are the settings I put on the hardened pod: non-root,
capabilities dropped, seccomp, no privilege escalation. trivy had never seen
my manifests and still scored the hardened workload as the least risky. The
rest of the table is the remediation backlog.

## Assessment two: kube-bench, and the findings that were mine

trivy reads objects. The [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
also checks component flags, file permissions and kubelet config, the node
half the blocked collector would have covered. I ran
[kube-bench](https://github.com/aquasecurity/kube-bench) as a Job on the
control-plane node, with a toleration for its `NoSchedule` taint and the
host paths mounted read-only.

The registry policy came up again here. The image is written
`docker.io/aquasec/kube-bench:v0.9.1` on purpose. The short form
`aquasec/kube-bench` contains a slash and does not start with an approved
registry, so the policy's CEL rule would deny it. I wrote the image the long
way to meet my own policy.

```
== Summary total ==
62 checks PASS
17 checks FAIL
51 checks WARN
```

`kind` is a development tool, not a hardened distribution, so failures were
expected. Several came from `kind` defaults: `--profiling` left
on for the API server, controller manager and scheduler (1.2.15, 1.3.2,
1.4.1), kubelet file permissions looser than 600 (4.1.1, 4.1.9), and PKI
ownership not `root:root` (1.1.19), because `kind` runs the components inside
a container.

The failures worth the run were the ones that pointed back at choices I had
made that day:

```
[FAIL] 1.2.17 Ensure that the --audit-log-maxage argument is set to 30 or as appropriate (Automated)
[FAIL] 1.2.18 Ensure that the --audit-log-maxbackup argument is set to 10 or as appropriate (Automated)
[FAIL] 1.2.19 Ensure that the --audit-log-maxsize argument is set to 100 or as appropriate (Automated)
[FAIL] 5.1.1 Ensure that the cluster-admin role is only used where required (Automated)
```

I had turned the audit log on with 7 days and 3 backups and no size limit.
CIS wants 30, 10 and 100. The control is present, but below the benchmark's
threshold, which is the gap an auditor asks about after "is it on?". And 5.1.1
flagged the `k8s-admins` to `cluster-admin` binding I had made earlier that
day for the identity work below. The benchmark caught my own broad grant.

The `policies` section came back 0 PASS, 6 FAIL, 29 WARN. WARN means "check
this yourself": a benchmark can point at `cluster-admin` or a wildcard, but it
cannot judge whether the grant is justified.

## Assessment three: Squawk on the files, before they reach the cluster

trivy and kube-bench look at a running cluster. I also wanted the same class
of checks run on the files, the way a pipeline would run them on a pull
request. [Squawk](https://github.com/ryayres-fox/squawk), my own scanner,
drives open-source tools one service at a time. Its `compliance` service runs
checkov, trivy-config and hadolint on the repository:

```
squawk run compliance --repo .
```

| Tool | What it read | Findings |
| --- | --- | --- |
| checkov | the Kubernetes manifests (17 resources) | 52 |
| trivy-config | 9 scan targets | 48 |
| hadolint | the one Dockerfile | 0 |

checkov and trivy-config flagged the same kind of gaps the live scan found:
missing resource limits, no read-only root filesystem, capabilities not
dropped. They found them from the YAML, before the object exists. Squawk also
refused to call the run clean, because one tool had nothing to read:

```
SQUAWK 7600 — lost communications: a result from fewer scanners is a floor, not a clean scan
    zizmor read nothing (no workflow files)
```

The `customs` service (syft, grype, osv-scanner) read the app's
`requirements.txt`. grype and osv-scanner each reported 11 vulnerabilities in
`urllib3==1.26.4`, including CVE-2021-33503 and CVE-2023-43804. They were
caught at the manifest, before any image was built.

## Identity from the identity provider, not from the cluster

Kubernetes has no user database. There is no "create user" command. The API
server can instead trust an OpenID Connect issuer: a caller presents a signed
ID token, the API server checks the signature against the issuer and passes
the username and groups claims to RBAC
([OIDC tokens](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens)).
I gave the cluster a Keycloak realm with a `kubernetes` client, two groups,
`k8s-admins` and `k8s-viewers`, one test user in each, and a group-membership
mapper that puts a `groups` claim in the token. The API server got five flags:

```yaml
oidc-issuer-url: https://$KEYCLOAK:8443/realms/k8s
oidc-client-id: kubernetes
oidc-username-claim: preferred_username
oidc-groups-claim: groups
oidc-ca-file: /etc/kubernetes/pki/keycloak-ca.crt
```

The RBAC names no person. Both bindings have `kind: Group` subjects:
`k8s-admins` to `cluster-admin`, `k8s-viewers` to the built-in read-only
`view` role. Membership in Keycloak is the only lever. Removing someone from
a group in the identity provider removes their cluster access, with no change
to the cluster.

Two things broke on the way.

The API server could not reach the issuer. Keycloak sat behind a published
port, then on host networking, and both times the `kind` node container could
not reach it. The Kali host firewall blocks that container-to-host path, and
changing it needs root. Putting Keycloak and the node on one dedicated Docker
network fixed it, since traffic on the same bridge is not host-firewalled.
The issuer URL is a network dependency as well as a setting.

The login looked like it worked when it had not. My first test sent the token
with a normal kubeconfig, and `kubectl auth whoami` came back
`kubernetes-admin`, authenticated by X509. `kubectl` had presented the admin
client certificate in the TLS handshake, and the API server authenticated
that before it looked at the token. OIDC was being bypassed without an error.
The fix was a kubeconfig with the cluster CA and no client credentials, so
the bearer token is the only identity on offer.

With that kubeconfig I fetched a token for each user from Keycloak with the
direct password grant, and asked the API server who I was and what I could do:

```
## ryan (Keycloak group k8s-admins -> cluster-admin)
Username     https://$KEYCLOAK:8443/realms/k8s#ryan
Groups       [k8s-admins system:authenticated]
can-i create deployments -A : yes
can-i delete nodes          : yes

## vic (Keycloak group k8s-viewers -> view, read-only)
Username     https://$KEYCLOAK:8443/realms/k8s#vic
Groups       [k8s-viewers system:authenticated]
can-i get pods -A           : yes
can-i create deployments    : no
delete ns kube-system       : Error from server (Forbidden): namespaces "kube-system" is forbidden:
  User "https://$KEYCLOAK:8443/realms/k8s#vic" cannot delete resource "namespaces" ...
```

The fields to read are `Username` and `Groups`. The username is the issuer
URL plus the user name, which shows the ID token was used rather than the
admin certificate. The groups come from the Keycloak claim, and the denial
names the external identity.

The issuer prefix is the API server's default, to stop an external name from
colliding with a built-in one. In production I would set
`--oidc-username-prefix` and `--oidc-groups-prefix` explicitly and bind RBAC
to the prefixed names. Real clusters also log in through the browser with the
`kubectl oidc-login` plugin; the password grant tests the same validation
path in the API server.

## What I learned

- A control can block the tool that checks it. My registry policy stopped
  trivy, and the right response was a scoped, recorded exception, not a
  weaker policy.
- An assessment is worth running on my own cluster for the findings that are
  mine. kube-bench flagged an audit log that was on but below the benchmark,
  and a `cluster-admin` grant I made the same day.
- A benchmark WARN is a question for a person. It points at a binding or a
  wildcard. It cannot say whether that grant is justified.
- `whoami` is the first check after any authentication change. A client
  certificate beat my token without an error, and only reading the username
  showed it.
- Group-bound RBAC moves access decisions to the identity provider. No person
  appears in a binding, so leaving a group is the whole offboarding step.
- The managed equivalent on AKS is Entra ID groups bound to cluster roles,
  with audit through diagnostic settings and Defender for Containers running
  the CIS checks. Azure owns the control plane, so the `master` and `etcd`
  sections of kube-bench are not the customer's to run.

## Next

The audit log works, but it sits in a file on the control-plane node and
only I read it. Next is shipping it to the Malcolm sensor and building
alerts on the changes in the policy table: a `cluster-admin` grant and a
deleted NetworkPolicy first. After that, the controls from today move into a
git repository that the cluster reconciles from, so a hand edit is drift
that gets reverted and recorded.
