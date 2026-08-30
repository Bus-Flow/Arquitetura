resource "random_id" "lambda_prefix" {
  byte_length = 4
}

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

locals {
  lambda_ingestion_name      = "${random_id.lambda_prefix.hex}-ingestion"
  lambda_ingestion_gtfs_name = "${random_id.lambda_prefix.hex}-ingestion-gtfs"
  lambda_etl_name            = "${random_id.lambda_prefix.hex}-etl"
}

/*==== Lambda Ingestion Function (Tempo Real) ====*/
resource "aws_lambda_function" "ingestion" {
  function_name    = local.lambda_ingestion_name
  handler          = "ingestion.lambda_handler"
  runtime          = "python3.9"
  role             = data.aws_iam_role.lab_role.arn
  filename         = "${path.module}/lambda_function/ingestion.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/ingestion.zip")
  timeout          = 120
  memory_size      = 1024

  layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python39:28"
  ]

  environment {
    variables = {
      BUCKET_RAW      = var.raw_name
      SNS_TOPIC_ARN   = var.topic_arn
      SPTRANS_TOKEN   = var.sptrans_token
      OPENWEATHER_KEY = var.openweather_key
      HERE_API_KEY    = var.here_api_key
    }
  }

  tags = {
    Name = "lambda-ingestion-busflow"
  }
}

/*==== Lambda Ingestion GTFS Function (Diária / 12h Inteligente) ====*/
resource "aws_lambda_function" "ingestion_gtfs" {
  function_name    = local.lambda_ingestion_gtfs_name
  handler          = "ingestion_gtfs.lambda_handler"
  runtime          = "python3.9"
  role             = data.aws_iam_role.lab_role.arn
  filename         = "${path.module}/lambda_function/ingestion_gtfs.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/ingestion_gtfs.zip")
  timeout          = 180
  memory_size      = 512

  layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python39:28"
  ]

  environment {
    variables = {
      BUCKET_RAW       = var.raw_name
      SNS_TOPIC_ARN    = var.topic_arn
      SPTRANS_USERNAME = var.sptrans_username
      SPTRANS_PASSWORD = var.sptrans_password
    }
  }

  tags = {
    Name = "lambda-ingestion-gtfs-busflow"
  }
}

/*==== Lambda ETL Function ====*/
resource "aws_lambda_function" "etl" {
  function_name    = local.lambda_etl_name
  handler          = "etl.lambda_handler"
  runtime          = "python3.9"
  role             = data.aws_iam_role.lab_role.arn
  filename         = "${path.module}/lambda_function/etl.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function/etl.zip")
  timeout          = 180
  memory_size      = 1024
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }

  layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python39:28"
  ]

  environment {
    variables = {
      BUCKET_RAW     = var.raw_name
      BUCKET_TRUSTED = var.trusted_name
      SNS_TOPIC_ARN  = var.topic_arn
      EMAIL_LIST     = jsonencode(var.email_list)
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
    filter_prefix       = "realtime/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

/*==== Gatilhos EventBridge: Ingestão em Tempo Real ====*/
resource "aws_cloudwatch_event_rule" "schedule_realtime_off_peak" {
  for_each            = var.schedule_realtime_off_peak_expressions
  name                = "busflow-schedule-realtime-off-peak-${each.key}"
  description         = "Dispara a ingestao de tempo real a cada 1 hora fora do pico, das 06h as 17h e das 19h as 22h (Brasilia)"
  schedule_expression = each.value
}

resource "aws_cloudwatch_event_target" "target_realtime_off_peak" {
  for_each  = aws_cloudwatch_event_rule.schedule_realtime_off_peak
  rule      = each.value.name
  target_id = "IngestionRealtimeOffPeakTarget-${each.key}"
  arn       = aws_lambda_function.ingestion.arn
}

resource "aws_lambda_permission" "allow_eventbridge_realtime_off_peak" {
  for_each      = aws_cloudwatch_event_rule.schedule_realtime_off_peak
  statement_id  = "AllowEventBridgeRealtimeOffPeak-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = each.value.arn
}

resource "aws_cloudwatch_event_rule" "schedule_realtime_peak" {
  name                = "busflow-schedule-realtime-peak"
  description         = "Dispara a ingestao de tempo real a cada 30 minutos das 17h as 19h (Brasilia)"
  schedule_expression = var.schedule_realtime_peak_expression
}

resource "aws_cloudwatch_event_target" "target_realtime_peak" {
  rule      = aws_cloudwatch_event_rule.schedule_realtime_peak.name
  target_id = "IngestionRealtimePeakTarget"
  arn       = aws_lambda_function.ingestion.arn
}

resource "aws_lambda_permission" "allow_eventbridge_realtime_peak" {
  statement_id  = "AllowEventBridgeRealtimePeakInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule_realtime_peak.arn
}

/*==== Gatilho EventBridge: Ingestão GTFS (a cada 12 horas) ====*/
resource "aws_cloudwatch_event_rule" "schedule_gtfs" {
  name                = "busflow-schedule-gtfs"
  description         = "Dispara a checagem e ingestao do GTFS da SPTrans a cada 12 horas"
  schedule_expression = var.schedule_gtfs_expression
}

resource "aws_cloudwatch_event_target" "target_gtfs" {
  rule      = aws_cloudwatch_event_rule.schedule_gtfs.name
  target_id = "IngestionGTFSTarget"
  arn       = aws_lambda_function.ingestion_gtfs.arn
}

resource "aws_lambda_permission" "allow_eventbridge_gtfs" {
  statement_id  = "AllowEventBridgeGTFSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion_gtfs.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule_gtfs.arn
}
