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
  vpc_id      = var.vpc_id

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
  subnet_id                   = var.subnet_id
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

  user_data = <<-EOF
              #!/bin/bash
              echo "=== Inicializando EC2 BusFlow (busflow-rf-ec2) ==="
              dnf update -y
              dnf install -y postgresql15 git python3-pip
              pip3 install pandas numpy scikit-learn psycopg2-binary joblib boto3
              echo "=== Ambiente de Machine Learning configurado com sucesso! ==="
              EOF

  tags = {
    Name = "busflow-rf-ec2"
  }
}

/*==== Security Group para EC2 Grafana (Web & SSH) ====*/
resource "aws_security_group" "grafana_sg" {
  name        = "busflow-grafana-ec2-sg"
  description = "Acesso SSH e Grafana Web para a EC2 Grafana"
  vpc_id      = var.vpc_id

  ingress {
    description = "Acesso SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  ingress {
    description = "Acesso Web Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "busflow-grafana-ec2-sg"
  }
}

/*==== EC2 Grafana - Subnet Pública ====*/
resource "aws_instance" "ec2-grafana" {
  ami                         = var.ami != "" ? var.ami : data.aws_ssm_parameter.al2023_ami[0].value
  instance_type               = var.instance_type_public
  key_name                    = aws_key_pair.generated_key.key_name
  subnet_id                   = var.subnet_id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.ec2_ssh.id, aws_security_group.grafana_sg.id]
  iam_instance_profile        = var.iam_instance_profile_name

  root_block_device {
    volume_size = var.volume_size
    volume_type = var.volume_type
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  user_data = <<-EOF
              #!/bin/bash
              echo "=== Inicializando EC2 Grafana (busflow-grafana-ec2) ==="
              dnf update -y
              cat <<EOR > /etc/yum.repos.d/grafana.repo
              [grafana]
              name=grafana
              baseurl=https://rpm.grafana.com
              repo_gpgcheck=1
              enabled=1
              gpgcheck=1
              gpgkey=https://rpm.grafana.com/gpg.key
              sslverify=1
              sslcacert=/etc/pki/tls/certs/ca-bundle.crt
              EOR
              dnf install -y grafana postgresql15
              systemctl daemon-reload
              systemctl enable --now grafana-server
              echo "=== Grafana instalado e iniciado com sucesso! ==="
              EOF

  tags = {
    Name = "busflow-grafana-ec2"
  }
}



