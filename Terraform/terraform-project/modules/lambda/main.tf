resource "random_id" "lambda_prefix" {
  byte_length = 4
}

locals {
  lambda_ingestion_name  = "${random_id.lambda_prefix.hex}-ingestion"
  lambda_etl_name        = "${random_id.lambda_prefix.hex}-etl"
  lambda_orchestrator_name = "${random_id.lambda_prefix.hex}-orchestrator"
}

/*==== Lambda Ingestion Function ====*/
resource "aws_lambda_function" "ingestion" {
  function_name = local.lambda_ingestion_name
  handler       = "ingestion.lambda_handler"
  runtime       = "python3.9"
  role          = aws_iam_role.lambda_role.arn
  filename      = "${path.module}/lambda_function/ingestion.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/ingestion.zip")
  timeout       = 60
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
      RDS_HOST          = var.rds_endpoint
      RDS_USER          = var.rds_username
      RDS_PASSWORD      = var.rds_password
      RDS_DATABASE      = var.rds_database
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
  role          = aws_iam_role.lambda_role.arn
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
      RDS_HOST          = var.rds_endpoint
      RDS_USER          = var.rds_username
      RDS_PASSWORD      = var.rds_password
      RDS_DATABASE      = var.rds_database
      SNS_TOPIC_ARN     = var.topic_arn
      EMAIL_LIST        = jsonencode(var.email_list)
    }
  }

  tags = {
    Name = "lambda-etl-busflow"
  }
}

/*==== Lambda Orchestrator Function ====*/
resource "aws_lambda_function" "orchestrator" {
  function_name = local.lambda_orchestrator_name
  handler       = "orchestrator.lambda_handler"
  runtime       = "python3.9"
  role          = aws_iam_role.lambda_role.arn
  filename      = "${path.module}/lambda_function/orchestrator.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/orchestrator.zip")
  timeout       = 60

  environment {
    variables = {
      INGESTION_FUNCTION_ARN = aws_lambda_function.ingestion.arn
      ETL_FUNCTION_ARN       = aws_lambda_function.etl.arn
      SNS_TOPIC_ARN          = var.topic_arn
    }
  }

  tags = {
    Name = "lambda-orchestrator-busflow"
  }
}

/*==== IAM Role para Lambdas ====*/
resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role-busflow"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "lambda-execution-role-busflow"
  }
}

/*==== IAM Policies para Lambda ====*/
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "lambda-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.raw_arn,
          "${var.raw_arn}/*",
          var.trusted_arn,
          "${var.trusted_arn}/*",
          var.prediction_arn,
          "${var.prediction_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_sns_access" {
  name = "lambda-sns-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.topic_arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_invoke" {
  name = "lambda-invoke"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.ingestion.arn,
          aws_lambda_function.etl.arn
        ]
      }
    ]
  })
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

/*==== EventBridge Rule para Orchestrator (cron job) ====*/
resource "aws_cloudwatch_event_rule" "orchestrator_trigger" {
  name                = "orchestrator-schedule-busflow"
  description         = "Trigger Lambda Orchestrator every hour"
  schedule_expression = "rate(1 hour)"

  tags = {
    Name = "orchestrator-trigger-busflow"
  }
}

resource "aws_cloudwatch_event_target" "orchestrator_target" {
  rule      = aws_cloudwatch_event_rule.orchestrator_trigger.name
  target_id = "LambdaOrchestrator"
  arn       = aws_lambda_function.orchestrator.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestrator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.orchestrator_trigger.arn
}


