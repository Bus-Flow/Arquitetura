variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/24"
}

variable "private_subnet_id" {
  description = "ID da subnet privada para SageMaker"
  type        = string
}

variable "trusted_bucket_arn" {
  description = "ARN do bucket Trusted"
  type        = string
}

variable "prediction_bucket_arn" {
  description = "ARN do bucket Prediction"
  type        = string
}

variable "notebook_instance_type" {
  description = "Tipo de instância do notebook SageMaker"
  type        = string
  default     = "ml.t3.medium"
}
