/*==== RDS Aurora MySQL Database ====*/

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "db-subnet-group-busflow"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "db-subnet-group-busflow"
  }
}

resource "aws_rds_cluster_instance" "db_instance" {
  identifier           = "db-busflow"
  cluster_identifier   = aws_rds_cluster.db_cluster.id
  instance_class       = var.instance_class
  engine               = "aurora-mysql"
  engine_version       = var.engine_version
  publicly_accessible  = false

  tags = {
    Name = "db-busflow-instance"
  }
}

resource "aws_rds_cluster" "db_cluster" {
  cluster_identifier              = "db-cluster-busflow"
  engine                          = "aurora-mysql"
  engine_version                  = var.engine_version
  database_name                   = var.database_name
  master_username                 = var.master_username
  master_password                 = var.master_password
  db_subnet_group_name            = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids          = [aws_security_group.rds_sg.id]
  storage_encrypted               = true
  backup_retention_period         = var.backup_retention_period
  preferred_backup_window         = "03:00-04:00"
  preferred_maintenance_window    = "sun:04:00-sun:05:00"
  skip_final_snapshot             = false
  final_snapshot_identifier       = "db-cluster-busflow-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  enabled_cloudwatch_logs_exports = ["audit", "error", "general", "slowquery"]
  
  tags = {
    Name = "db-cluster-busflow"
  }
}

/*==== Security Group para RDS ====*/
resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Allow MySQL from Lambda and EC2"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [var.lambda_sg_id, var.ec2_sg_id]
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

