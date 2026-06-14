resource "aws_s3_bucket" "raw" {
  bucket = "raw-busflow-2026-2"
  force_destroy = true
  
  tags = {
    Name = "raw-bucket-busflow"
  }
}

resource "aws_s3_bucket" "trusted" {
  bucket = "trusted-busflow-2026-2"
  force_destroy = true
  
  tags = {
    Name = "trusted-bucket-busflow"
  }
}


/*==== S3 Bucket Versioning ====*/
resource "aws_s3_bucket_versioning" "raw_versioning" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "trusted_versioning" {
  bucket = aws_s3_bucket.trusted.id
  versioning_configuration {
    status = "Enabled"
  }
}



