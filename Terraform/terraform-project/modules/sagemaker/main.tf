/*==== IAM Role para SageMaker ====*/
resource "aws_iam_role" "sagemaker_role" {
  name = "sagemaker-execution-role-busflow"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "sagemaker-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "sagemaker_policy" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "sagemaker_s3_policy" {
  name = "sagemaker-s3-access"
  role = aws_iam_role.sagemaker_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.trusted_bucket_arn,
          "${var.trusted_bucket_arn}/*",
          var.prediction_bucket_arn,
          "${var.prediction_bucket_arn}/*"
        ]
      }
    ]
  })
}

/*==== SageMaker Notebook Instance ====*/
resource "aws_sagemaker_notebook_instance" "ml_notebook" {
  name                    = "ml-notebook-busflow"
  role_arn                = aws_iam_role.sagemaker_role.arn
  instance_type           = var.notebook_instance_type
  subnet_id               = var.private_subnet_id
  security_groups         = [aws_security_group.sagemaker_sg.id]
  associate_public_ip_address = false

  tags = {
    Name = "ml-notebook-busflow"
  }
}

resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "notebook_config" {
  name = "ml-notebook-config-busflow"

  on_create = [base64encode(file("${path.module}/lifecycle_scripts/on_create.sh"))]
  on_start  = [base64encode(file("${path.module}/lifecycle_scripts/on_start.sh"))]
}

resource "aws_sagemaker_notebook_instance" "ml_notebook_with_config" {
  name                            = "ml-notebook-busflow"
  role_arn                        = aws_iam_role.sagemaker_role.arn
  instance_type                   = var.notebook_instance_type
  subnet_id                       = var.private_subnet_id
  security_groups                 = [aws_security_group.sagemaker_sg.id]
  lifecycle_config_name           = aws_sagemaker_notebook_instance_lifecycle_configuration.notebook_config.name
  associate_public_ip_address     = false

  depends_on = [aws_sagemaker_notebook_instance_lifecycle_configuration.notebook_config]

  tags = {
    Name = "ml-notebook-busflow"
  }
}

/*==== Security Group para SageMaker ====*/
resource "aws_security_group" "sagemaker_sg" {
  name        = "sagemaker-security-group"
  description = "Security group for SageMaker"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sagemaker-security-group-busflow"
  }
}

