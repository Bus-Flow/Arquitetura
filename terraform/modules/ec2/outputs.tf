output "ec2_web_app_id" {
  value = aws_instance.ec2-web-app.id
}

output "ec2_web_app_ip" {
  value = aws_instance.ec2-web-app.public_ip
}

output "ec2_grafana_id" {
  description = "ID da EC2 Grafana"
  value       = aws_instance.ec2-grafana.id
}

output "ec2_grafana_ip" {
  description = "IP público da EC2 Grafana"
  value       = aws_instance.ec2-grafana.public_ip
}

output "security_group_id" {
  description = "ID do Security Group da EC2 BusFlow"
  value       = aws_security_group.ec2_ssh.id
}

output "private_key_pem" {
  description = "Chave SSH privada RSA (PEM) para acesso à EC2"
  value       = tls_private_key.generated_key.private_key_pem
  sensitive   = true
}
