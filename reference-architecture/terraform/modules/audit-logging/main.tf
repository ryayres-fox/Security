# Audit logging baseline.
#
# The control this module is really about is AU-9 — audit records that cannot be
# quietly modified. Enabling a trail is the easy half; making the trail's own
# storage tamper-evident is the half that gets skipped.
#
# Every Checkov exception in this file is inline, names the check, and carries a
# written justification. A blanket `soft_fail` would make this module pass too,
# and would mean nothing.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  region     = data.aws_region.current.name

  trail_arn     = "arn:${local.partition}:cloudtrail:${local.region}:${local.account_id}:trail/${var.trail_name}"
  log_group_arn = "arn:${local.partition}:logs:${local.region}:${local.account_id}:log-group:${aws_cloudwatch_log_group.trail.name}"
}

# ---------------------------------------------------------------------------
# Server access log target
#
# S3 server access logging needs somewhere to go. That target is itself a bucket,
# which raises the same question one hop out — the recursion has to terminate
# somewhere, and it terminates here, deliberately and in writing.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "access_logs" {
  # checkov:skip=CKV_AWS_145:S3 server access logging cannot deliver to a bucket encrypted with a customer-managed KMS key — the service does not support it. SSE-S3 is applied instead. This is a platform constraint, so the honest options were an unencrypted-by-CMK log target or no access logging at all; the tradeoff is recorded here rather than resolved by dropping the control.
  # checkov:skip=CKV_AWS_18:This bucket IS the server-access-log target. Logging it to itself creates a write amplification loop; a third bucket relocates the question without answering it. The termination point is documented rather than hidden.
  # checkov:skip=CKV_AWS_144:Cross-region replication is an availability decision with real cost, and access logs are not the audit record of record — the CloudTrail objects are, and those are protected by Object Lock COMPLIANCE below.
  # checkov:skip=CKV2_AWS_62:Event notifications here would fire in proportion to read volume against the audit bucket, producing cost and noise with no detection value.
  bucket        = "${var.bucket_name}-access-logs"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    apply_server_side_encryption_by_default {
      # S3 server access logging cannot deliver to a bucket encrypted with a
      # customer-managed key. SSE-S3 is the strongest option the service
      # supports for this target — a genuine service constraint, not a choice.
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "expire-access-logs"
    status = "Enabled"
    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    expiration {
      days = var.access_log_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    # An abandoned multipart upload is billed indefinitely and is invisible in
    # the object listing — a storage cost with no owner and no expiry.
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "access_logs" {
  statement {
    sid    = "S3ServerAccessLogsDelivery"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.access_logs.arn}/*"]
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.audit.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.access_logs.arn, "${aws_s3_bucket.access_logs.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  policy = data.aws_iam_policy_document.access_logs.json
}

# ---------------------------------------------------------------------------
# Audit record store
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "audit" {
  # checkov:skip=CKV_AWS_144:Cross-region replication is a caller-level availability decision, and a costly one. The tamper-evidence property this module is responsible for comes from Object Lock COMPLIANCE plus CloudTrail digest files, neither of which replication improves. A caller that needs multi-region durability composes it around this module; forcing it here would price the module out of the environments that need the control most.
  bucket        = var.bucket_name
  force_destroy = false

  # Object Lock cannot be enabled after creation. Getting this wrong means
  # rebuilding the bucket later, which in a regulated environment means a
  # migration and an assessor conversation.
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode = "COMPLIANCE" # GOVERNANCE can be bypassed with a privileged role
      days = var.retention_days
    }
  }
  depends_on = [aws_s3_bucket_versioning.audit]
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket                  = aws_s3_bucket.audit.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_logging" "audit" {
  bucket        = aws_s3_bucket.audit.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "s3-access/"
}

# Transitions only. No expiration rule: an Object Lock COMPLIANCE retention makes
# an expiration action a no-op until the lock lapses, so writing one would be a
# lifecycle policy that reads as a deletion schedule and does not delete. The
# retention period is the deletion schedule.
resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    id     = "tier-audit-records"
    status = "Enabled"
    filter {}

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ---------------------------------------------------------------------------
# Notification path
#
# SI-4 depends on someone finding out. A trail nobody is subscribed to is a
# forensic resource, not a detective control.
# ---------------------------------------------------------------------------

resource "aws_sns_topic" "audit_events" {
  name              = "${var.trail_name}-audit-events"
  kms_master_key_id = var.kms_key_arn
}

data "aws_iam_policy_document" "audit_events" {
  statement {
    sid    = "AllowCloudTrailPublish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["SNS:Publish"]
    resources = [aws_sns_topic.audit_events.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }

  statement {
    sid    = "AllowS3Publish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    actions   = ["SNS:Publish"]
    resources = [aws_sns_topic.audit_events.arn]
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.audit.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "audit_events" {
  arn    = aws_sns_topic.audit_events.arn
  policy = data.aws_iam_policy_document.audit_events.json
}

resource "aws_s3_bucket_notification" "audit" {
  bucket = aws_s3_bucket.audit.id

  topic {
    topic_arn = aws_sns_topic.audit_events.arn
    events    = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_sns_topic_policy.audit_events]
}

# ---------------------------------------------------------------------------
# CloudWatch Logs delivery
#
# The S3 copy is the record of record. The CloudWatch copy is what a metric
# filter and an alarm can actually watch in near real time.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "trail" {
  name              = "/aws/cloudtrail/${var.trail_name}"
  retention_in_days = var.cloudwatch_retention_days
  kms_key_id        = var.kms_key_arn
}

data "aws_iam_policy_document" "trail_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }
}

data "aws_iam_policy_document" "trail_logs" {
  statement {
    effect  = "Allow"
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    # Scoped to this trail's own log streams. `logs:*` on `*` is the usual
    # shortcut here and it hands the trail role write access to every log group
    # in the account, including the ones recording its own misuse.
    resources = ["${local.log_group_arn}:log-stream:${local.account_id}_CloudTrail_${local.region}*"]
  }
}

resource "aws_iam_role" "trail" {
  name                 = "${var.trail_name}-cloudwatch-delivery"
  assume_role_policy   = data.aws_iam_policy_document.trail_assume.json
  permissions_boundary = var.permissions_boundary_arn
}

resource "aws_iam_role_policy" "trail" {
  name   = "cloudwatch-delivery"
  role   = aws_iam_role.trail.id
  policy = data.aws_iam_policy_document.trail_logs.json
}

# ---------------------------------------------------------------------------
# The trail
# ---------------------------------------------------------------------------

# CloudTrail will not create a trail until the bucket policy already permits the
# writes. The aws:SourceArn condition is what stops this policy from being usable
# by any other account's trail — the confused-deputy path that an over-broad
# service-principal grant leaves open.
data "aws_iam_policy_document" "audit" {
  statement {
    sid    = "AWSCloudTrailAclCheck"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.audit.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }

  statement {
    sid    = "AWSCloudTrailWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.audit.arn}/AWSLogs/${local.account_id}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }

  # SC-8: the encryption-at-rest configuration above says nothing about the
  # transport. Without this, a plaintext PutObject is still accepted.
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.audit.arn, "${aws_s3_bucket.audit.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "audit" {
  bucket = aws_s3_bucket.audit.id
  policy = data.aws_iam_policy_document.audit.json
}

resource "aws_cloudtrail" "main" {
  name           = var.trail_name
  s3_bucket_name = aws_s3_bucket.audit.id
  kms_key_id     = var.kms_key_arn
  sns_topic_name = aws_sns_topic.audit_events.arn

  # AU-9: without this, a modified log file is indistinguishable from a real one.
  enable_log_file_validation = true

  is_multi_region_trail         = true
  include_global_service_events = true
  enable_logging                = true

  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.trail.arn}:*"
  cloud_watch_logs_role_arn  = aws_iam_role.trail.arn

  depends_on = [
    aws_s3_bucket_policy.audit,
    aws_sns_topic_policy.audit_events,
    aws_iam_role_policy.trail,
  ]
}
