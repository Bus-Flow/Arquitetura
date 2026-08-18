module "net" {
    source = "../network"
}

resource "aws_key_pair" "generated_key"{
    key_name = var.key_pair_name
    public_key = file("terraform_key.pem.pub")
}

/*==== EC2 Web App - Subnet Pública 1 ====*/
resource "aws_instance" "ec2-web-app" {
  ami                         = var.ami
  availability_zone           = var.a_zones[0]
  instance_type               = var.instance_type_public
  key_name                    = aws_key_pair.generated_key.key_name
  subnet_id                   = module.net.subnet_public_ids[0]
  associate_public_ip_address = true
  vpc_security_group_ids      = [module.net.sg_id]
  ebs_optimized               = true

  ebs_block_device {
    device_name = "/dev/sda1"
    volume_size = var.volume_size
    volume_type = var.volume_type
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "ec2-web-app-busflow"
  }
}



