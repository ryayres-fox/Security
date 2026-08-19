# Security policy

## Scope

This repository contains reference implementations and lab material. It is not production software
and carries no support commitment.

## Reporting

- **A security issue** — a credential or internal detail that slipped through, an insecure default,
  a control that doesn't do what it claims — use the **[Report a vulnerability](https://github.com/ryayres-fox/Security/security/advisories/new)**
  button on the Security tab. It opens a **private** advisory, so a real disclosure stays private
  until it's fixed.
- **A correction or improvement** — a flawed pattern, a better approach, a typo — open a **pull
  request** from a fork. Issues are disabled on this repository, so a PR is the way in. Corrections
  are the point of publishing this.

## Controls on this repository

| Control | Where | Catches |
| --- | --- | --- |
| `.gitignore` | client-side | accidents only — advisory, not a control |
| `.githooks/pre-commit` | local, opt-in | staged career or credential material |
| `repo hygiene` | CI | the same, on **tracked** files, on a machine that is not the author's |
| `IaC scan` (Checkov) | CI | infrastructure misconfiguration, `soft_fail: false` |
| `secrets scan` (Gitleaks) | CI | credential material anywhere in history |
| secret scanning + push protection | GitHub | a leaked secret in history, and one **at push time before it reaches the remote** |
| `custom policies` | CI | that the policy set **registers and fires**, not merely that it ran |
| branch protection | GitHub | `main` is locked read-only; no direct pushes, force-pushes, or deletions |

## Push protection — the one control CI cannot provide

The CI `secrets scan` runs *after* a push, so by the time it fails, the secret has already reached
the remote. **GitHub push protection** is the only control here that blocks a secret *before* it
leaves the machine — it rejects the push itself. It is free on public repositories and is enabled on
this one, alongside secret scanning over the full history.

## What this repository deliberately does not contain

No credentials, no account identifiers, no ARNs, no internal hostnames, and nothing derived from
any employer or client environment. Every example is synthetic. If you believe something here
discloses more than it should, report it privately with the **Report a vulnerability** button above.
