output "alb_dns_name" {
  description = "DNS name do Application Load Balancer"
  value       = aws_lb.app_lb.dns_name
}

output "alb_zone_id" {
  description = "Zone ID do Application Load Balancer"
  value       = aws_lb.app_lb.zone_id
}

output "target_group_arn" {
  description = "ARN do Target Group"
  value       = aws_lb_target_group.app_tg.arn
}