# AWS Textract Pipeline

This uses AWS infrastructure to deliver PDF images to Textract and extract the response text. For a visual
representation of the infrastructure, see **textract-pipeline-flowchart.pdf** in the repository.

## Description

This project is designed to automate document processing using AWS Textract in combination with AWS Lambda, S3, IAM, and SNS services. 
The main functionality revolves around triggering a Lambda function whenever a PDF is uploaded to an S3 bucket. 
The Lambda function processes the document using Textract and performs subsequent operations as required.

## Getting Started

### Requirements

* AWS Account
* Terraform and Python installed

### Provider Configuration

The provider block configures the specified provider, in this case, AWS. 
You need to provide your AWS credentials and the region where you want to deploy your resources.

```
provider "aws" {
    access_key = var.access_key
    secret_key = var.secret_key
    region     = var.region
}
```

### Variables

* secret_key: Your AWS secret key.
* access_key: Your AWS access key.
* region: AWS region where resources will be created.
* project_name: A tag for resource identification.
* bucket_name: The name of the S3 bucket to be created.
* email: Email address for notifications.

## Resources

### S3 Bucket

An S3 bucket is created for storing PDF documents. The bucket's name is derived from the **bucket_name** variable.

### AWS Lambda Function

A Lambda function (**call-textract**) is configured for processing the documents using AWS Textract. 
The function is set with a Python 3.10 runtime, has a timeout of 300 seconds, and has a reserved concurrency of 15.

### IAM Roles and Policies

IAM roles and policies are configured for various services including Lambda, S3, Textract, and CloudWatch.

### SNS Topic

An SNS topic (**on_lambda_function_error**) is set up as a dead letter queue for error notification. Notifications are sent to the email address provided in the **email** variable.

## Usage

1. Initialize **Terraform**: Run **terraform init** to initialize the working directory.
2. **Plan**: Execute **terraform plan** to preview the changes.
3. **Apply**: Apply the changes useing **terraform apply**.
4. When uploading PDF images to the S3 bucket, be sure to assign each PDF image a subfolder beneath the **pdf_images** folder; otherwise, the lambda function may run into issues.
5. Keep in mind that the 

## Authors

Andrew Steurer

linkedin.com/in/andrewsteurer
