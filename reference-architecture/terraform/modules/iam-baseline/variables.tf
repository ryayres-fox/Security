variable "name_prefix" {
  type        = string
  description = "Prefix for IAM resource names."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,30}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric with hyphens, 2-31 characters."
  }
}

variable "boundary_allowed_actions" {
  type        = list(string)
  description = "Service action prefixes the boundary permits at its ceiling. Deny statements in the module carve out of this set. Keep it to the services the environment actually uses — an unused service in this list is standing permission nobody is watching."
  default = [
    "s3:*",
    "ec2:*",
    "eks:*",
    "logs:*",
    "kms:Decrypt",
    "kms:Encrypt",
    "kms:GenerateDataKey*",
    "kms:DescribeKey",
    "secretsmanager:GetSecretValue",
    "ssm:GetParameter*",
    "sts:AssumeRole",
  ]

  validation {
    condition     = !contains(var.boundary_allowed_actions, "*")
    error_message = "A bare '*' defeats the boundary entirely. Enumerate the services in use."
  }

  validation {
    condition     = !contains(var.boundary_allowed_actions, "iam:*")
    error_message = "iam:* inside the boundary permits privilege escalation paths the Deny statements are there to close."
  }
}

variable "allowed_regions" {
  type        = list(string)
  default     = []
  description = "Regions in which resource creation is permitted. Empty disables the region guardrail; global services are exempted regardless."
}

variable "oidc_provider_url" {
  type        = string
  default     = null
  description = "OIDC issuer URL for workload identity federation (e.g. https://token.actions.githubusercontent.com). Null disables the federated role entirely."
}

variable "oidc_claim_host" {
  type        = string
  default     = "token.actions.githubusercontent.com"
  description = "Host portion used to build condition keys, e.g. '<host>:sub'. Must match the issuer."
}

variable "oidc_audiences" {
  type        = list(string)
  default     = ["sts.amazonaws.com"]
  description = "Accepted `aud` claim values."
}

variable "oidc_thumbprints" {
  type        = list(string)
  default     = []
  description = "TLS thumbprints for the OIDC provider."
}

variable "oidc_allowed_subjects" {
  type        = list(string)
  default     = []
  description = "Fully-qualified `sub` claims permitted to assume the CI role, matched with StringEquals. Example: 'repo:example-org/example-repo:ref:refs/heads/main'."

  validation {
    condition     = alltrue([for s in var.oidc_allowed_subjects : !strcontains(s, "*")])
    error_message = "Wildcards are rejected. 'repo:org/repo:*' trusts every branch, tag and pull request, including a branch an outside contributor can create. List fully-qualified subjects."
  }
}

variable "max_session_duration" {
  type        = number
  default     = 3600
  description = "Maximum federated session lifetime in seconds."

  validation {
    condition     = var.max_session_duration >= 900 && var.max_session_duration <= 14400
    error_message = "Session duration must be between 900 and 14400 seconds; a deploy role should sit near the floor."
  }
}

variable "manage_password_policy" {
  type        = bool
  default     = false
  description = "Whether this module owns the account password policy. Account-wide and singleton: only one module in an account may set it."
}
