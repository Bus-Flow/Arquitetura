resource "random_id" "lambda_prefix" {
  byte_length = 4
}

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

locals {
  lambda_ingestion_name  = "${random_id.lambda_prefix.hex}-ingestion"
  lambda_etl_name        = "${random_id.lambda_prefix.hex}-etl"
}

/*==== Lambda Ingestion Function ====*/
resource "aws_lambda_function" "ingestion" {
  function_name = local.lambda_ingestion_name
  handler       = "ingestion.lambda_handler"
  runtime       = "python3.9"
  role          = data.aws_iam_role.lab_role.arn
  filename      = "${path.module}/lambda_function/ingestion.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/ingestion.zip")
  timeout       = 60

  layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python39:28"
  ]

  environment {
    variables = {
      BUCKET_RAW        = var.raw_name
      SNS_TOPIC_ARN     = var.topic_arn
    }
  }

  tags = {
    Name = "lambda-ingestion-busflow"
  }
}

/*==== Lambda ETL Function ====*/
resource "aws_lambda_function" "etl" {
  function_name = local.lambda_etl_name
  handler       = "etl.lambda_handler"
  runtime       = "python3.9"
  role          = data.aws_iam_role.lab_role.arn
  filename      = "${path.module}/lambda_function/etl.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/etl.zip")
  timeout       = 120
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }

  layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python39:28"
  ]

  environment {
    variables = {
      BUCKET_RAW        = var.raw_name
      BUCKET_TRUSTED    = var.trusted_name
      SNS_TOPIC_ARN     = var.topic_arn
      EMAIL_LIST        = jsonencode(var.email_list)
    }
  }

  tags = {
    Name = "lambda-etl-busflow"
  }
}






/*==== S3 Trigger para Lambda ETL ====*/
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.etl.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.raw_arn
}

resource "aws_s3_bucket_notification" "bucket_trigger" {
  bucket = var.raw_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.etl.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}




