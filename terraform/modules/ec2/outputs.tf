output "ec2_web_app_id" {
  value = aws_instance.ec2-web-app.id
}



output "ec2_web_app_ip" {
  value = aws_instance.ec2-web-app.public_ip
}


