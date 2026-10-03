output "ec2_web_app_id" {
  value = aws_instance.ec2-web-app.id
}

output "ec2_web_app_ip" {
  value = aws_instance.ec2-web-app.public_ip
}

output "security_group_id" {
  description = "ID do Security Group da EC2 BusFlow"
  value       = aws_security_group.ec2_ssh.id
}
