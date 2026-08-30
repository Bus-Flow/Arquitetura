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
  default     = "07a60d55d2de72360de37d156be6824c972ecc0a95ec74e2bbba660c5c412d9d"
}

variable "openweather_key" {
  description = "API Key do serviço meteorológico OpenWeather"
  type        = string
  sensitive   = true
  default     = "ff7cc980c0bc6823b91cbd0d1af58610"
}

variable "here_api_key" {
  description = "API Key do serviço de tráfego HERE (opcional/fallback ativo se vazio)"
  type        = string
  sensitive   = true
  default     = "ddL58af4Y1mhBw2I_Br4GNGGPXywpKtxoCedVeozQGY"
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
  default     = "Fgandb25_#"
}

# ==============================================================================
# Configurações de Agendamento (EventBridge Triggers)
# ==============================================================================
variable "schedule_realtime_off_peak_expressions" {
  description = "Expressões EventBridge para ingestão em tempo real fora do pico, das 06h às 17h e das 19h às 22h (horário de Brasília)"
  type = map(string)
  default = {
    morning = "cron(0 9-19 ? * * *)"
    evening = "cron(0 22-23 ? * * *)"
    late    = "cron(0 0-1 ? * * *)"
  }
}

variable "schedule_realtime_peak_expression" {
  description = "Expressão EventBridge para ingestão em tempo real no pico, das 17h às 19h (horário de Brasília)"
  type        = string
  default     = "cron(0/30 20-21 ? * * *)"
}

variable "schedule_gtfs_expression" {
  description = "Expressão de agendamento para a Ingestão do GTFS (ex: a cada 12 horas)"
  type        = string
  default     = "rate(12 hours)"
}
