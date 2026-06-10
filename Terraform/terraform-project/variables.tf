variable "email_list" {
  description = "Lista de e-mails para o SNS e Lambda"
  type        = list(string)
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/24"
}

variable "rds_master_username" {
  description = "RDS Master username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "rds_master_password" {
  description = "RDS Master password"
  type        = string
  sensitive   = true
}

variable "rds_database_name" {
  description = "RDS Database name"
  type        = string
  default     = "busflowdb"
}

