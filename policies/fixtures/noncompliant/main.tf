# Deliberately non-compliant. Every resource here violates exactly one custom
# check, so a test can assert which check fired rather than only that something
# did.
#
# This file is never applied and never validated against a provider. It exists
# so the policy set can be proven to MATCH, not merely to load — a check that
# registers and never fires is the same fail-open as a check that never
# registers, relocated one step later.

resource "aws_s3_bucket_object_lock_configuration" "governance_mode" {
  # CKV_CAC_1: GOVERNANCE can be bypassed by a principal holding
  # s3:BypassGovernanceRetention. The mode is the control.
  bucket = "example-audit"
  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 365
    }
  }
}

resource "aws_iam_role" "no_boundary" {
  # CKV_CAC_2: no permissions_boundary, so any later policy attachment is
  # unbounded.
  name               = "example-unbounded"
  assume_role_policy = "{}"
}

data "aws_iam_policy_document" "wildcard_subject" {
  # CKV_CAC_3: StringLike with a trailing wildcard trusts every ref in the
  # repository, including a branch an outside contributor can create.
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::000000000000:oidc-provider/token.actions.githubusercontent.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:example-org/example-repo:*"]
    }
  }
}
