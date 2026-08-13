# iam-baseline

Permission boundaries, workload identity federation, and no static credentials.

## What it enforces

| Control | How |
|---|---|
| **AC-2** | Boundary denies creation of users, roles and login profiles |
| **AC-6** | Permission boundary attached **at role creation**, not retrofitted |
| **AC-6(5)** | Privilege-escalation paths explicitly denied, including removing one's own boundary |
| **AC-4** | Resource creation confined to approved regions, with global services exempted |
| **IA-2** | Federated OIDC role; no access keys exist for this identity |
| **IA-2(1)** | Trust bound to fully-qualified subjects; wildcards rejected at plan time |
| **IA-5** | Boundary denies `CreateAccessKey` and `CreateLoginProfile` |
| **AU-9** | Boundary denies CloudTrail, Config, GuardDuty, Security Hub and KMS tampering |

## The two things this module exists to get right

### 1. The OIDC trust policy

The common form of a GitHub Actions trust policy is a `StringLike` on `sub`
with a trailing wildcard:

```json
"token.actions.githubusercontent.com:sub": "repo:example-org/example-repo:*"
```

That trusts **every ref in the repository** — every branch, every tag, and on
many configurations every pull request, including one opened from a fork. The
role is scoped, the boundary is attached, the policy passes review, and anyone
who can create a branch can assume the deploy role.

This module uses `StringEquals` against fully-qualified subjects, and the
variable rejects `*` outright:

```hcl
oidc_allowed_subjects = [
  "repo:example-org/example-repo:ref:refs/heads/main",
  "repo:example-org/example-repo:environment:production",
]
```

Adding a trusted caller becomes a reviewed Terraform change rather than a
`git push`. The validation is what makes that stick — a comment saying "don't
use wildcards here" is advice, and advice does not survive a deadline.

### 2. The boundary is a ceiling, not a policy

Effective permission is `identity policy ∩ boundary`. The boundary's Allow
statement is the ceiling; the Deny statements carve out of it. This is why
Checkov's wildcard checks are skipped on this resource, with the reasoning
written inline — a permission boundary that enumerates resources cannot
function, because it constrains roles whose resources are unknown when the
boundary is authored.

`DenyBoundaryAlteration` is the statement that matters most. Without it, any
role that can attach a policy can attach `AdministratorAccess` to itself, and
the boundary becomes a suggestion. Note that removing one's own boundary is
denied specifically — it is the first move in most escalation paths and the one
most often left out.

`DenyAuditTampering` is the statement an incident depends on. A principal that
can stop CloudTrail logging can do everything else without a record of it.

## Policy exceptions

Five Checkov checks are skipped on `aws_iam_policy.boundary`, each inline with
its reasoning, and each declared in `controls.yaml` so the coverage report shows
them. Run `python tools/control_coverage.py` to see them alongside the controls.

## Usage

```hcl
module "iam_baseline" {
  source      = "./modules/iam-baseline"
  name_prefix = "example"

  allowed_regions = ["us-east-1", "us-west-2"]

  oidc_provider_url = "https://token.actions.githubusercontent.com"
  oidc_thumbprints  = [var.github_oidc_thumbprint]
  oidc_allowed_subjects = [
    "repo:example-org/example-repo:ref:refs/heads/main",
  ]

  manage_password_policy = true  # account-wide singleton; only one module may set it
}
```

Then attach the boundary to every workload role:

```hcl
resource "aws_iam_role" "worker" {
  name                 = "example-worker"
  assume_role_policy   = data.aws_iam_policy_document.worker_assume.json
  permissions_boundary = module.iam_baseline.boundary_arn
}
```

## Verifying it

```bash
terraform init -backend=false && terraform validate
checkov -d . --compact          # 0 failed, 5 skipped-with-reason
```

Plan-time validation you can trigger deliberately, which is the point of having
it: set `oidc_allowed_subjects = ["repo:org/repo:*"]` and `terraform plan` fails
before anything is created.
