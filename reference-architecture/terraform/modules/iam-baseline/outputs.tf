output "boundary_arn" {
  value       = aws_iam_policy.boundary.arn
  description = "AC-6 evidence: the permission-boundary ARN every workload role must carry."
}

output "boundary_name" {
  value       = aws_iam_policy.boundary.name
  description = "Name of the permission boundary policy."
}

output "ci_role_arn" {
  value       = try(aws_iam_role.ci[0].arn, null)
  description = "IA-2 evidence: federated CI role ARN, or null when OIDC is not configured."
}

output "ci_role_has_boundary" {
  value       = try(aws_iam_role.ci[0].permissions_boundary, null) != null
  description = "AC-6 evidence: the federated role is created with a boundary attached, not retrofitted."
}

output "oidc_allowed_subjects" {
  value       = var.oidc_allowed_subjects
  description = "IA-2 evidence: the exact, wildcard-free subjects trusted to assume the CI role."
}
