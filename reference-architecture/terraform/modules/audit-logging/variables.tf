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
