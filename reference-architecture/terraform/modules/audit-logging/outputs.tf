# Outputs are the module's contract. Everything exported here is something a
# caller — or an assessor — has a legitimate reason to reference. The control
# attributes are exported deliberately: a composition test can assert on them
# without reaching into the module's internals.

output "bucket_arn" {
  value       = aws_s3_bucket.audit.arn
  description = "ARN of the audit log bucket."
}

output "bucket_name" {
  value       = aws_s3_bucket.audit.id
  description = "Name of the audit log bucket."
}

output "trail_arn" {
  value       = aws_cloudtrail.main.arn
  description = "ARN of the CloudTrail trail."
}

output "log_file_validation_enabled" {
  value       = aws_cloudtrail.main.enable_log_file_validation
  description = "AU-9 evidence: digest files are produced, so a modified log file is detectable."
}

output "object_lock_retention_days" {
  value       = var.retention_days
  description = "AU-11 evidence: Object Lock COMPLIANCE retention applied to audit records."
}

output "multi_region_trail" {
  value       = aws_cloudtrail.main.is_multi_region_trail
  description = "AU-2 evidence: management events are captured in every region, not just the home region."
}
