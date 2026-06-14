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



variable "topic_arn" {
  description = "ARN do tópico SNS"
  type        = string
}

variable "email_list" {
  description = "Lista de e-mails que vão receber notificações do SNS"
  type        = list(string)
}



variable "lambda_sg_id" {
  description = "Security Group ID para Lambda"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs das subnets privadas para Lambda VPC"
  type        = list(string)
}
