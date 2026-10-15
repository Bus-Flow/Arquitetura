resource "random_id" "s3_suffix" {
  byte_length = 4
}

locals {
  raw_name     = "raw-busflow-2026-${random_id.s3_suffix.hex}"
  trusted_name = "trusted-busflow-2026-${random_id.s3_suffix.hex}"
  raw_arn      = "arn:aws:s3:::${local.raw_name}"
  trusted_arn  = "arn:aws:s3:::${local.trusted_name}"
}

# Buckets criados via AWS CLI para contornar SCP que bloqueia
# s3:GetBucketObjectLockConfiguration e s3:GetBucketVersioning nas contas Academy.
# O provider AWS 5.x chama essas APIs no Read pós-Create, independente de lifecycle rules.
resource "null_resource" "s3_buckets" {
  triggers = {
    raw     = local.raw_name
    trusted = local.trusted_name
  }

  provisioner "local-exec" {
    command    = "aws s3api create-bucket --bucket ${local.raw_name} --region us-east-1"
    on_failure = continue
  }

  provisioner "local-exec" {
    command    = "aws s3api create-bucket --bucket ${local.trusted_name} --region us-east-1"
    on_failure = continue
  }

  provisioner "local-exec" {
    when       = destroy
    command    = "aws s3 rm s3://${self.triggers.raw} --recursive"
    on_failure = continue
  }

  provisioner "local-exec" {
    when       = destroy
    command    = "aws s3api delete-bucket --bucket ${self.triggers.raw} --region us-east-1"
    on_failure = continue
  }

  provisioner "local-exec" {
    when       = destroy
    command    = "aws s3 rm s3://${self.triggers.trusted} --recursive"
    on_failure = continue
  }

  provisioner "local-exec" {
    when       = destroy
    command    = "aws s3api delete-bucket --bucket ${self.triggers.trusted} --region us-east-1"
    on_failure = continue
  }
}
