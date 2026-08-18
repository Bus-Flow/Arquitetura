variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs das subnets privadas"
  type        = list(string)
}

variable "lambda_sg_id" {
  description = "Security Group ID das Lambdas"
  type        = string
}

variable "ec2_sg_id" {
  description = "Security Group ID das EC2s"
  type        = string
}

variable "instance_class" {
  description = "Classe da instância RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "engine_version" {
  description = "Versão do PostgreSQL"
  type        = string
  default     = "14"
}

variable "database_name" {
  description = "Nome do banco de dados"
  type        = string
  default     = "busflowdb"
}

variable "master_username" {
  description = "Usuário master do banco"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "master_password" {
  description = "Senha master do banco"
  type        = string
  sensitive   = true
}

variable "backup_retention_period" {
  description = "Dias de retenção de backups"
  type        = number
  default     = 7
}

variable "sagemaker_sg_id" {
  description = "Security Group ID do SageMaker"
  type        = string
}

