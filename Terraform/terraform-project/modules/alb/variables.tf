variable "vpc_id" {
  description = "ID da VPC"
  type        = string
}

variable "subnet_ids" {
  description = "IDs das subnets públicas para o ALB"
  type        = list(string)
}

variable "security_group_id" {
  description = "ID do Security Group"
  type        = string
}

variable "target_instances" {
  description = "Lista dos IDs das instâncias EC2 para o target group"
  type        = list(string)
}