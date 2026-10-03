# ==============================================================================
# Variáveis de Infraestrutura e Rede
# ==============================================================================
variable "vpc_cidr" {
  description = "Bloco CIDR da VPC BusFlow"
  type        = string
  default     = "10.0.0.0/24"
}

variable "email_list" {
  description = "Lista de e-mails para notificações de alertas SNS"
  type        = list(string)
}

variable "ec2_ssh_allowed_cidr" {
  description = "IP público autorizado a acessar SSH na EC2, no formato IPv4 /32"
  type        = string

  validation {
    condition     = can(cidrnetmask(var.ec2_ssh_allowed_cidr)) && endswith(var.ec2_ssh_allowed_cidr, "/32")
    error_message = "ec2_ssh_allowed_cidr deve conter o seu IP público no formato IPv4 /32."
  }
}

variable "ec2_vpc_id" {
  description = "VPC do Learner Lab; vazio usa a VPC padrão da região"
  type        = string
  default     = ""

  validation {
    condition     = var.ec2_vpc_id == "" || var.ec2_subnet_id != ""
    error_message = "Informe ec2_subnet_id junto com ec2_vpc_id para selecionar explicitamente uma subnet pública."
  }
}

variable "ec2_subnet_id" {
  description = "Subnet pública do Learner Lab; vazio seleciona uma subnet da VPC configurada"
  type        = string
  default     = ""
}

variable "ec2_iam_instance_profile_name" {
  description = "Nome do perfil de instância IAM já fornecido pelo Learner Lab"
  type        = string
  default     = "LabInstanceProfile"
}

variable "ec2_instance_type" {
  description = "Tipo da EC2; t3.small é o padrão, com t2.small e t3.medium como alternativas"
  type        = string
  default     = "t3.small"

  validation {
    condition     = contains(["t3.small", "t2.small", "t3.medium"], var.ec2_instance_type)
    error_message = "ec2_instance_type deve ser t3.small, t2.small ou t3.medium."
  }
}

variable "ec2_volume_size" {
  description = "Tamanho do volume raiz gp3 da EC2, em GiB"
  type        = number
  default     = 20

  validation {
    condition     = var.ec2_volume_size >= 15 && var.ec2_volume_size <= 20
    error_message = "ec2_volume_size deve estar entre 15 e 20 GiB."
  }
}

# ==============================================================================
# Variáveis do Banco de Dados (RDS PostgreSQL)
# ==============================================================================
variable "rds_master_username" {
  description = "Usuário master do banco RDS PostgreSQL"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "rds_master_password" {
  description = "Senha master do banco RDS PostgreSQL"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.rds_master_password) >= 8
    error_message = "rds_master_password deve ter pelo menos 8 caracteres."
  }
}

variable "rds_database_name" {
  description = "Nome da base de dados no RDS"
  type        = string
  default     = "busflowdb"
}

# ==============================================================================
# Credenciais e Chaves de APIs Externas
# ==============================================================================
variable "sptrans_token" {
  description = "Token de autenticação na API Olho Vivo da SPTrans"
  type        = string
  sensitive   = true
}

variable "openweather_key" {
  description = "API Key do serviço meteorológico OpenWeather"
  type        = string
  sensitive   = true
}

variable "here_api_key" {
  description = "API Key do serviço de tráfego HERE (opcional/fallback ativo se vazio)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sptrans_username" {
  description = "Usuário de login no portal de desenvolvedores da SPTrans (para download GTFS)"
  type        = string
  default     = "freitazgiovanna"
}

variable "sptrans_password" {
  description = "Senha de login no portal de desenvolvedores da SPTrans"
  type        = string
  sensitive   = true
}

# ==============================================================================
# Configurações de Agendamento (EventBridge Triggers)
# ==============================================================================
variable "schedule_realtime_off_peak_expressions" {
  description = "Expressões EventBridge para ingestão em tempo real fora do pico"
  type        = map(string)

  default = {
    morning   = "cron(0 9-11 ? * * *)"
    afternoon = "cron(0/20 12-16 ? * * *)"
    evening   = "cron(0 22-23 ? * * *)"
    late      = "cron(0 0-1 ? * * *)"
  }
}

variable "schedule_realtime_peak_expression" {
  description = "Expressão EventBridge para ingestão em tempo real no pico, das 17h às 19h, a cada 10 minutos"
  type        = string
  default     = "cron(0/10 17-19 ? * * *)"
}

variable "schedule_gtfs_expression" {
  description = "Expressão de agendamento para a Ingestão do GTFS (ex: a cada 12 horas)"
  type        = string
  default     = "rate(12 hours)"
}
