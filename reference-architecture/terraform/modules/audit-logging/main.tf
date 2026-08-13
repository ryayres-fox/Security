# Audit logging baseline.
#
# The control this module is really about is AU-9 — audit records that cannot be
# quietly modified. Enabling a trail is the easy half; making the trail's own
# storage tamper-evident is the half that gets skipped.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

resource "aws_s3_bucket" "audit" {
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

resource "aws_cloudtrail" "main" {
  name           = var.trail_name
  s3_bucket_name = aws_s3_bucket.audit.id
  kms_key_id     = var.kms_key_arn

  # AU-9: without this, a modified log file is indistinguishable from a real one.
  enable_log_file_validation = true

  is_multi_region_trail         = true
  include_global_service_events = true
  enable_logging                = true

  depends_on = [aws_s3_bucket_policy.audit]
}
