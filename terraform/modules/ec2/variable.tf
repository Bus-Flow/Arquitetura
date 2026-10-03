variable "ami" {
  type        = string
  description = "AMI override; vazio usa a AMI mais recente do Amazon Linux 2023 x86_64"
  default     = ""
}

variable "a_zones" {
  type        = list(string)
  description = "Availability zones"
  default     = ["us-east-1a", "us-east-1b"]
}

variable "instance_type_public" {
  type    = string
  default = "t3.small"
}

variable "instance_type_private" {
  type    = string
  default = "t3.small"
}

variable "volume_size" {
  type    = number
  default = 20
}

variable "volume_type" {
  type    = string
  default = "gp3"
}

variable "key_pair_name" {
  type    = string
  default = "terraform_key"
}

variable "vpc_id" {
  type        = string
  description = "VPC do Learner Lab; vazio usa a VPC padrão da região"
  default     = ""

  validation {
    condition     = var.vpc_id == "" || var.subnet_id != ""
    error_message = "Informe subnet_id junto com vpc_id para selecionar explicitamente uma subnet pública."
  }
}

variable "subnet_id" {
  type        = string
  description = "Subnet pública do Learner Lab; vazio seleciona uma subnet da VPC configurada"
  default     = ""
}

variable "iam_instance_profile_name" {
  type        = string
  description = "Nome do perfil de instância IAM existente fornecido pelo Learner Lab"
  default     = "LabInstanceProfile"
}

variable "ssh_allowed_cidr" {
  type        = string
  description = "IP público autorizado a acessar SSH, no formato IPv4 /32"

  validation {
    condition     = can(cidrnetmask(var.ssh_allowed_cidr)) && endswith(var.ssh_allowed_cidr, "/32")
    error_message = "ssh_allowed_cidr deve conter o seu IP público no formato IPv4 /32."
  }
}
