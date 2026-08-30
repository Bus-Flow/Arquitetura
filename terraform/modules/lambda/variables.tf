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

# Credenciais e Parâmetros das APIs
variable "sptrans_token" {
  description = "Token da API Olho Vivo SPTrans"
  type        = string
  default     = ""
}

variable "openweather_key" {
  description = "API Key OpenWeather"
  type        = string
  default     = ""
}

variable "here_api_key" {
  description = "API Key HERE Traffic"
  type        = string
  default     = ""
}

variable "sptrans_username" {
  description = "Usuário Portal SPTrans"
  type        = string
  default     = ""
}

variable "sptrans_password" {
  description = "Senha Portal SPTrans"
  type        = string
  default     = ""
}

variable "schedule_realtime_off_peak_expressions" {
  description = "Expressões EventBridge para ingestão em tempo real fora do pico"
  type        = map(string)
}

variable "schedule_realtime_peak_expression" {
  description = "Expressão EventBridge para ingestão em tempo real no pico"
  type        = string
}

variable "schedule_gtfs_expression" {
  description = "Expressão de agendamento EventBridge GTFS"
  type        = string
  default     = "rate(12 hours)"
}
