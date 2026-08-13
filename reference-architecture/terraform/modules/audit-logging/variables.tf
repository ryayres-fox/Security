variable "bucket_name" {
  type        = string
  description = "Name of the audit log bucket. Must be globally unique."
}

variable "trail_name" {
  type        = string
  description = "Name of the CloudTrail trail."
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN. AWS-managed keys do not satisfy SC-12 key-ownership expectations in a FedRAMP context."
}

variable "retention_days" {
  type        = number
  default     = 365
  description = "Object Lock retention in days."

  validation {
    condition     = var.retention_days >= 365
    error_message = "AU-11 baseline requires at least 365 days of audit record retention."
  }
}

variable "cloudwatch_retention_days" {
  type        = number
  default     = 365
  description = "Retention for the CloudWatch Logs copy of the trail. CloudWatch accepts only a fixed set of values, which is why this is validated against a list rather than a floor."

  validation {
    condition = contains(
      [365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.cloudwatch_retention_days
    )
    error_message = "Must be a CloudWatch-accepted retention value of 365 days or more, to stay consistent with the AU-11 baseline."
  }
}

variable "access_log_retention_days" {
  type        = number
  default     = 90
  description = "Retention for S3 server access logs. These are an access record for the audit store, not audit records themselves, so they are not held to the AU-11 floor."

  validation {
    condition     = var.access_log_retention_days >= 90
    error_message = "Access logs must be retained at least 90 days to remain useful for incident reconstruction."
  }
}

variable "permissions_boundary_arn" {
  type        = string
  default     = null
  description = "Optional permissions boundary for the CloudWatch delivery role. AC-6: a boundary caps what the role can ever be granted, independent of who edits its policy later."
}
