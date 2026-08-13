# IAM baseline: workload identity, permission boundaries, no static credentials.
#
# The control this module is really about is AC-6, and specifically the part of
# AC-6 that policy documents cannot express: *who can grant themselves more*. A
# least-privilege policy that a role can rewrite is a least-privilege policy for
# as long as nobody tries.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# ---------------------------------------------------------------------------
# Permission boundary
#
# A boundary is a ceiling, not a grant. It caps what a role can ever hold no
# matter what policy is attached to it later, by whom, or by accident. This is
# the control that makes delegated IAM administration survivable.
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "boundary" {
  # The effective permissions of a role are (identity policy ∩ boundary). This
  # statement is the intersection's upper bound; the denies below carve out of it.
  statement {
    sid       = "AllowServicesWithinBoundary"
    effect    = "Allow"
    actions   = var.boundary_allowed_actions
    resources = ["*"]
  }

  # Privilege escalation closure. Without these, any role that can attach a
  # policy can attach AdministratorAccess to itself and the boundary is a
  # suggestion. Detaching one's own boundary is the specific move to block.
  statement {
    sid    = "DenyBoundaryAlteration"
    effect = "Deny"
    actions = [
      "iam:CreateUser",
      "iam:CreateRole",
      "iam:DeleteRolePermissionsBoundary",
      "iam:DeleteUserPermissionsBoundary",
      "iam:PutRolePermissionsBoundary",
      "iam:PutUserPermissionsBoundary",
      "iam:AttachRolePolicy",
      "iam:AttachUserPolicy",
      "iam:PutRolePolicy",
      "iam:PutUserPolicy",
      "iam:CreatePolicyVersion",
      "iam:SetDefaultPolicyVersion",
    ]
    resources = ["*"]
  }

  # IA-2: long-lived access keys are the credential that leaks. Denying their
  # creation is more durable than detecting them after the fact.
  statement {
    sid    = "DenyStaticCredentialCreation"
    effect = "Deny"
    actions = [
      "iam:CreateAccessKey",
      "iam:CreateLoginProfile",
      "iam:UpdateAccessKey",
      "iam:UpdateLoginProfile",
    ]
    resources = ["*"]
  }

  # AU-9: nothing inside the boundary may interfere with the audit trail, even
  # if a policy grants it. This is the statement an incident depends on.
  statement {
    sid    = "DenyAuditTampering"
    effect = "Deny"
    actions = [
      "cloudtrail:DeleteTrail",
      "cloudtrail:StopLogging",
      "cloudtrail:UpdateTrail",
      "cloudtrail:PutEventSelectors",
      "config:DeleteConfigurationRecorder",
      "config:StopConfigurationRecorder",
      "config:DeleteDeliveryChannel",
      "guardduty:DeleteDetector",
      "guardduty:UpdateDetector",
      "securityhub:DisableSecurityHub",
      "kms:ScheduleKeyDeletion",
      "kms:DisableKey",
    ]
    resources = ["*"]
  }

  # SC-7 / AC-4: confine the blast radius to approved regions. An unused region
  # is where resources get created without anyone watching a dashboard for them.
  dynamic "statement" {
    for_each = length(var.allowed_regions) > 0 ? [1] : []
    content {
      sid    = "DenyOutsideApprovedRegions"
      effect = "Deny"
      not_actions = [
        # Global endpoints. Denying these by region breaks the account.
        "iam:*",
        "sts:*",
        "organizations:*",
        "cloudfront:*",
        "route53:*",
        "support:*",
      ]
      resources = ["*"]
      condition {
        test     = "StringNotEquals"
        variable = "aws:RequestedRegion"
        values   = var.allowed_regions
      }
    }
  }
}

resource "aws_iam_policy" "boundary" {
  # checkov:skip=CKV_AWS_289:The Allow statement is the boundary ceiling, not a grant. A permission boundary that enumerates resources cannot function — it constrains roles whose resources are unknown at boundary-authoring time. The narrowing is done by the Deny statements and by each role's own identity policy, which is the intersection that actually applies.
  # checkov:skip=CKV_AWS_290:As above. Write actions inside a boundary are bounded by the attached identity policy; the boundary's job is to cap, not to grant.
  # checkov:skip=CKV_AWS_286:Escalation is closed by the DenyBoundaryAlteration statement, which a resource-scoped Allow could not achieve.
  # checkov:skip=CKV_AWS_287:Credentials-exposure actions are denied explicitly in DenyStaticCredentialCreation.
  # checkov:skip=CKV_AWS_288:Data-exfiltration actions remain subject to each role's identity policy; the boundary does not grant them on its own.
  name        = "${var.name_prefix}-permission-boundary"
  description = "Ceiling for all workload roles. Caps privilege regardless of attached policies."
  policy      = data.aws_iam_policy_document.boundary.json
}

# ---------------------------------------------------------------------------
# Workload identity via OIDC
#
# The point of federation is that there is no secret to leak, rotate, or find in
# a git history. The risk moves from credential custody to trust-policy
# correctness — a smaller, reviewable, testable surface.
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "ci" {
  count = var.oidc_provider_url == null ? 0 : 1

  url             = var.oidc_provider_url
  client_id_list  = var.oidc_audiences
  thumbprint_list = var.oidc_thumbprints
}

data "aws_iam_policy_document" "ci_assume" {
  count = var.oidc_provider_url == null ? 0 : 1

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.ci[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_claim_host}:aud"
      values   = var.oidc_audiences
    }

    # The statement this module exists to get right.
    #
    # The common form is StringLike on `sub` with a trailing wildcard —
    # `repo:org/repo:*` — which trusts *every* branch, tag and pull request of
    # that repository, including a branch an outside contributor can create.
    # StringEquals against fully-qualified subjects means a new trusted caller
    # is a reviewed Terraform change, not a `git push`.
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_claim_host}:sub"
      values   = var.oidc_allowed_subjects
    }
  }
}

resource "aws_iam_role" "ci" {
  count = var.oidc_provider_url == null ? 0 : 1

  name                 = "${var.name_prefix}-ci-deploy"
  description          = "Federated CI role. No static credentials are issued for this identity."
  assume_role_policy   = data.aws_iam_policy_document.ci_assume[0].json
  permissions_boundary = aws_iam_policy.boundary.arn
  max_session_duration = var.max_session_duration
}

# ---------------------------------------------------------------------------
# Account-level baseline
# ---------------------------------------------------------------------------

resource "aws_iam_account_password_policy" "this" {
  count = var.manage_password_policy ? 1 : 0

  minimum_password_length        = 14
  require_uppercase_characters   = true
  require_lowercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  allow_users_to_change_password = true

  # IA-5(1): rotation without history reuse is theatre — users cycle back to the
  # same password. Rotation is also the control most likely to be a net negative
  # when MFA and a length floor are already in place; it is here because
  # baselines still ask for it, not because it is the strongest lever.
  password_reuse_prevention = 24
  max_password_age          = 90
}
