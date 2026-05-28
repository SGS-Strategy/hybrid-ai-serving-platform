# Terraform 설정
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "sgs-hasp-artifacts"
    key            = "terraform/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "sgs-hasp-terraform-lock"
    encrypt        = true
  }
}

# AWS Provider
provider "aws" {
  region = var.aws_region
}
