output "raw_name" {
    value = aws_s3_bucket.raw.bucket
}
output "raw_arn" {
    value = aws_s3_bucket.raw.arn
}
output "raw_id" {
    value = aws_s3_bucket.raw.id
}

output "trusted_name" {
    value = aws_s3_bucket.trusted.bucket
}
output "trusted_arn" {
    value = aws_s3_bucket.trusted.arn
}
output "trusted_id" {
    value = aws_s3_bucket.trusted.id
}