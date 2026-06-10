output "rds_endpoint" {
  description = "RDS Cluster endpoint"
  value       = aws_rds_cluster.db_cluster.endpoint
}

output "rds_reader_endpoint" {
  description = "RDS Cluster reader endpoint"
  value       = aws_rds_cluster.db_cluster.reader_endpoint
}

output "rds_port" {
  description = "RDS port"
  value       = aws_rds_cluster.db_cluster.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_rds_cluster.db_cluster.database_name
}

output "rds_sg_id" {
  description = "RDS Security Group ID"
  value       = aws_security_group.rds_sg.id
}
