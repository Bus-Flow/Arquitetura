variable "raw_name" {
  description = "Nome do bucket Raw"
  type        = string
}

variable "raw_arn" {
  description = "ARN do bucket Raw"
  type        = string
}

variable "trusted_name" {
  description = "Nome do bucket Trusted"
  type        = string
}

variable "trusted_arn" {
  description = "ARN do bucket Trusted"
  type        = string
}

variable "prediction_arn" {
  description = "ARN do bucket Prediction"
  type        = string
}

variable "topic_arn" {
  description = "ARN do tópico SNS"
  type        = string
}

variable "email_list" {
  description = "Lista de e-mails que vão receber notificações do SNS"
  type        = list(string)
}

variable "rds_endpoint" {
  description = "Endpoint do RDS"
  type        = string
}

variable "rds_username" {
  description = "Username do RDS"
  type        = string
  sensitive   = true
}

variable "rds_password" {
  description = "Password do RDS"
  type        = string
  sensitive   = true
}

variable "rds_database" {
  description = "Database name do RDS"
  type        = string
}

variable "lambda_sg_id" {
  description = "Security Group ID para Lambda"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs das subnets privadas para Lambda VPC"
  type        = list(string)
}
