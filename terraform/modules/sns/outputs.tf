output "topic_arn" {
  description = "ARN do tópico SNS para uso em outras partes da infraestrutura"
  value       = aws_sns_topic.notificacao_csv.arn
}