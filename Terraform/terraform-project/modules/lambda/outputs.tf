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


output "lambda_role_arn" {
  value = data.aws_iam_role.lab_role.arn
}

