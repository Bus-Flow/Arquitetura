terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}
provider "aws" {
  region  = "us-east-1"
}

module "net" {
    source = "./modules/network"
}

module "s3" {
  source = "./modules/s3"
}

module "sns" {
  source = "./modules/sns"
  email_list = var.email_list
}

module "rds" {
  source = "./modules/rds"
  vpc_id             = module.net.vpc_id
  private_subnet_ids = module.net.subnet_private_ids
  lambda_sg_id       = module.net.lambda_sg_id
  ec2_sg_id          = module.net.sg_id
  master_password    = var.rds_master_password
}

module "lambda" {
  source            = "./modules/lambda"
  email_list        = var.email_list
  raw_arn           = module.s3.raw_arn
  raw_name          = module.s3.raw_name
  trusted_name      = module.s3.trusted_name
  trusted_arn       = module.s3.trusted_arn
  prediction_arn    = module.s3.prediction_arn
  topic_arn         = module.sns.topic_arn
  rds_endpoint      = module.rds.rds_endpoint
  rds_username      = var.rds_master_username
  rds_password      = var.rds_master_password
  rds_database      = var.rds_database_name
  lambda_sg_id      = module.net.lambda_sg_id
  private_subnet_ids = module.net.subnet_private_ids
}

module "sagemaker" {
  source                = "./modules/sagemaker"
  vpc_id                = module.net.vpc_id
  vpc_cidr              = var.vpc_cidr
  private_subnet_id     = module.net.subnet_private_id
  trusted_bucket_arn    = module.s3.trusted_arn
  prediction_bucket_arn = module.s3.prediction_arn
}

module "ec2" {
    source = "./modules/ec2"
}

module "alb" {
  source            = "./modules/alb"
  vpc_id            = module.net.vpc_id
  subnet_ids        = module.net.subnet_public_ids
  security_group_id = module.net.sg_id
  target_instances  = [module.ec2.ec2_web_app_id, module.ec2.ec2_grafana_id]
}

# Outputs
output "alb_dns_name" {
  description = "DNS name do Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "ec2_web_app_ip" {
  description = "IP público da EC2 Web App"
  value       = module.ec2.ec2_web_app_ip
}

output "ec2_grafana_ip" {
  description = "IP público da EC2 Grafana"
  value       = module.ec2.ec2_grafana_ip
}

output "rds_endpoint" {
  description = "RDS Cluster endpoint"
  value       = module.rds.rds_endpoint
}

output "rds_reader_endpoint" {
  description = "RDS Reader endpoint"
  value       = module.rds.rds_reader_endpoint
}

output "sagemaker_notebook_name" {
  description = "SageMaker Notebook Instance name"
  value       = module.sagemaker.notebook_instance_name
}

output "lambda_ingestion_arn" {
  description = "Lambda Ingestion ARN"
  value       = module.lambda.lambda_ingestion_function_arn
}

output "lambda_etl_arn" {
  description = "Lambda ETL ARN"
  value       = module.lambda.lambda_etl_function_arn
}

output "lambda_orchestrator_arn" {
  description = "Lambda Orchestrator ARN"
  value       = module.lambda.lambda_orchestrator_function_arn
}

output "s3_raw_bucket" {
  description = "S3 Raw bucket name"
  value       = module.s3.raw_name
}

output "s3_trusted_bucket" {
  description = "S3 Trusted bucket name"
  value       = module.s3.trusted_name
}

output "s3_prediction_bucket" {
  description = "S3 Prediction bucket name"
  value       = module.s3.prediction_name
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = module.sns.topic_arn
}