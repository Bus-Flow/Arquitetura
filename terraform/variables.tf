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
variable "schedule_realtime_expression" {
  description = "Expressão de agendamento para a Ingestão em Tempo Real (ex: rate(5 minutes))"
  type        = string
  default     = "rate(5 minutes)"
}

variable "schedule_gtfs_expression" {
  description = "Expressão de agendamento para a Ingestão do GTFS (ex: a cada 12 horas)"
  type        = string
  default     = "rate(12 hours)"
}
