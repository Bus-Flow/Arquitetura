output "notebook_instance_arn" {
  description = "ARN da instância do notebook SageMaker"
  value       = aws_sagemaker_notebook_instance.ml_notebook_with_config.arn
}

output "notebook_instance_name" {
  description = "Nome da instância do notebook SageMaker"
  value       = aws_sagemaker_notebook_instance.ml_notebook_with_config.notebook_instance_name
}

output "sagemaker_role_arn" {
  description = "ARN da IAM role para SageMaker"
  value       = aws_iam_role.sagemaker_role.arn
}

output "sagemaker_sg_id" {
  description = "SageMaker Security Group ID"
  value       = aws_security_group.sagemaker_sg.id
}
