data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

/*==== SageMaker Notebook Instance ====*/
resource "aws_sagemaker_notebook_instance" "ml_notebook" {
  name                   = "ml-notebook-busflow"
  role_arn               = data.aws_iam_role.lab_role.arn
  instance_type          = var.notebook_instance_type
  subnet_id              = var.private_subnet_id
  security_groups        = [aws_security_group.sagemaker_sg.id]
  direct_internet_access = "Enabled"

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

