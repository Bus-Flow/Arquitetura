# Application Load Balancer
resource "aws_lb" "app_lb" {
  name               = "busflow-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.subnet_ids

  enable_deletion_protection = false

  tags = {
    Name = "busflow-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "app_tg" {
  name     = "busflow-target-group"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "busflow-target-group"
  }
}

# Target Group Attachment para EC2s
resource "aws_lb_target_group_attachment" "app_tg_attachment" {
  count            = length(var.target_instances)
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = var.target_instances[count.index]
  port             = 80
}

# Listener do ALB
resource "aws_lb_listener" "app_listener" {
  load_balancer_arn = aws_lb.app_lb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    
    forward {
      target_group {
        arn = aws_lb_target_group.app_tg.arn
      }
    }
  }
}
