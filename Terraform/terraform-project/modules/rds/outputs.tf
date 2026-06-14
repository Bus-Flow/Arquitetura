output "rds_endpoint" {
  description = "RDS DB instance address"
  value       = aws_db_instance.db_instance.address
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.db_instance.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.db_instance.db_name
}

output "rds_sg_id" {
  description = "RDS Security Group ID"
  value       = aws_security_group.rds_sg.id
}
