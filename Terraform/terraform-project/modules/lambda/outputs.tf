output "lambda_ingestion_function_name" {
  value = aws_lambda_function.ingestion.function_name
}

output "lambda_ingestion_function_arn" {
  value = aws_lambda_function.ingestion.arn
}

output "lambda_etl_function_name" {
  value = aws_lambda_function.etl.function_name
}

output "lambda_etl_function_arn" {
  value = aws_lambda_function.etl.arn
}

output "lambda_orchestrator_function_name" {
  value = aws_lambda_function.orchestrator.function_name
}

output "lambda_orchestrator_function_arn" {
  value = aws_lambda_function.orchestrator.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_role.arn
}

