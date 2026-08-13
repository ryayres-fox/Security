# The compliant counterpart. Every resource here satisfies the same check its
# non-compliant twin violates.
#
# This half matters as much as the other. A policy set that fails everything
# passes every "does it fire?" test and is still useless — it gets suppressed
# within a week, and a suppressed check reports success forever after.

resource "aws_s3_bucket_object_lock_configuration" "compliance_mode" {
  bucket = "example-audit"
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}

resource "aws_iam_role" "bounded" {
  name                 = "example-bounded"
  assume_role_policy   = "{}"
  permissions_boundary = "arn:aws:iam::000000000000:policy/example-permission-boundary"
}

data "aws_iam_policy_document" "exact_subject" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::000000000000:oidc-provider/token.actions.githubusercontent.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:example-org/example-repo:ref:refs/heads/main"]
    }
  }
}
