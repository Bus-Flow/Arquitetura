data "aws_vpc" "default" {
  count   = var.vpc_id == "" && var.subnet_id == "" ? 1 : 0
  default = true
}

data "aws_subnet" "selected" {
  count = var.subnet_id == "" ? 0 : 1
  id    = var.subnet_id
}

locals {
  selected_vpc_id = var.vpc_id != "" ? var.vpc_id : (
    var.subnet_id != "" ? data.aws_subnet.selected[0].vpc_id : data.aws_vpc.default[0].id
  )
  selected_subnet_id = var.subnet_id != "" ? var.subnet_id : data.aws_subnets.public[0].ids[0]
}

data "aws_subnets" "public" {
  count = var.subnet_id == "" ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [local.selected_vpc_id]
  }
}

data "aws_ssm_parameter" "al2023_ami" {
  count = var.ami == "" ? 1 : 0
  name  = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "tls_private_key" "generated_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = var.key_pair_name
  public_key = tls_private_key.generated_key.public_key_openssh
}

resource "aws_security_group" "ec2_ssh" {
  name        = "busflow-rf-ec2-ssh"
  description = "SSH access to the BusFlow RF EC2 from the configured IP"
  vpc_id      = local.selected_vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "ec2-web-app" {
  ami                         = var.ami != "" ? var.ami : data.aws_ssm_parameter.al2023_ami[0].value
  instance_type               = var.instance_type_public
  key_name                    = aws_key_pair.generated_key.key_name
  subnet_id                   = local.selected_subnet_id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.ec2_ssh.id]
  iam_instance_profile        = var.iam_instance_profile_name

  root_block_device {
    volume_size = var.volume_size
    volume_type = var.volume_type
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "busflow-rf-ec2"
  }
}



