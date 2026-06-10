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
  default     = "db.t3.small"
}

variable "engine_version" {
  description = "Versão do MySQL Aurora"
  type        = string
  default     = "5.7.mysql_aurora.2.11.2"
}

variable "database_name" {
  description = "Nome do banco de dados"
  type        = string
  default     = "busflowdb"
}

variable "master_username" {
  description = "Usuário master do banco"
  type        = string
  default     = "admin"
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

