/*==== RDS Aurora MySQL Database ====*/

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "db-subnet-group-busflow"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "db-subnet-group-busflow"
  }
}

resource "aws_db_instance" "db_instance" {
  identifier             = "db-busflow"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_type           = "gp2"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  db_name                = var.database_name
  username               = var.master_username
  password               = var.master_password
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
  publicly_accessible    = false

  tags = {
    Name = "db-busflow-instance"
  }
}

/*==== Security Group para RDS ====*/
resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Allow PostgreSQL access"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.lambda_sg_id, var.ec2_sg_id, var.sagemaker_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "rds-security-group-busflow"
  }
}

