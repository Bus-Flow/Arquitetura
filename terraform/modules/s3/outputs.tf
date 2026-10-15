output "raw_name" {
  value      = local.raw_name
  depends_on = [null_resource.s3_buckets]
}

output "raw_arn" {
  value      = local.raw_arn
  depends_on = [null_resource.s3_buckets]
}

output "raw_id" {
  value      = local.raw_name
  depends_on = [null_resource.s3_buckets]
}

output "trusted_name" {
  value      = local.trusted_name
  depends_on = [null_resource.s3_buckets]
}

output "trusted_arn" {
  value      = local.trusted_arn
  depends_on = [null_resource.s3_buckets]
}

output "trusted_id" {
  value      = local.trusted_name
  depends_on = [null_resource.s3_buckets]
}
