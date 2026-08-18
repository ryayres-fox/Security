# Security policy

## Scope

This repository contains reference implementations and lab material. It is not production software
and carries no support commitment.

## Reporting

Found something wrong — a flawed pattern, an insecure default, a control that doesn't do what it
claims? Open an issue. Corrections are the point of publishing this.

## Controls on this repository

| Control | Where | Catches |
| --- | --- | --- |
| `.gitignore` | client-side | accidents only — advisory, not a control |
| `.githooks/pre-commit` | local, opt-in | staged career or credential material |
| `repo hygiene` | CI | the same, on **tracked** files, on a machine that is not the author's |
| `IaC scan` (Checkov) | CI | infrastructure misconfiguration, `soft_fail: false` |
| `secrets scan` (Gitleaks) | CI | credential material anywhere in history |
| `custom policies` | CI | that the policy set **registers and fires**, not merely that it ran |
| branch protection | GitHub | direct pushes, force-pushes, deletions |

## One control that is not yet enabled

**GitHub secret scanning and push protection are off, because the repository is
private.** They require GitHub Advanced Security on a private repository —
verified, not assumed:

```
PATCH …/security_and_analysis[secret_scanning][status]=enabled
422  "Secret scanning is not available for this repository."
```

Both are **free on public repositories**. This repository is intended to become
public, so **enabling them is part of going public**, not a follow-up. Push
protection blocks a secret at push time, before it reaches the remote — which is
the one thing the CI gates above cannot do, since they run after the push.

## What this repository deliberately does not contain

No credentials, no account identifiers, no ARNs, no internal hostnames, and nothing derived from
any employer or client environment. Every example is synthetic. If you believe something here
discloses more than it should, please open an issue and say so.
