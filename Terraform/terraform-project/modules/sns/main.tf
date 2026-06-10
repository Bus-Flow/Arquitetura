resource "aws_sns_topic" "notificacao_csv" {
  name = "topico-processamento-csv-20250504"
}

resource "aws_sns_topic_subscription" "email_subscribers" {
  for_each = toset(var.email_list)

  topic_arn = aws_sns_topic.notificacao_csv.arn
  protocol  = "email"
  endpoint  = each.key
}