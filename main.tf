/*
-------------------------------
Provider Configuration
-------------------------------
*/

provider "aws" {
    access_key = var.access_key
    secret_key = var.secret_key
    region = var.region
}

variable "secret_key" {
  description = "Your AWS secret key"
  default = "null"
}

variable "access_key" {
  description = "Your AWS access key"
  default = "null"
}

variable "region" {
    description = "The region in which you would like your resources placed"
    default = "null"
}

/*
-------------------------------
S3 Bucket
-------------------------------
*/

variable "project_name" {
  default = "null"
  description = "The name under which you wish this project to be tagged."
}

resource "aws_s3_bucket" "textract_data_bucket" {
    bucket = var.bucket_name
    tags = {
      project = var.project_name
    }
}

variable "bucket_name" {
  default = "null"
  description = "The name of the S3 bucket you want to create"
  type = string
}

resource "aws_s3_bucket_policy" "allow_lambda_and_textract" {
    bucket = aws_s3_bucket.textract_data_bucket.id
    policy = data.aws_iam_policy_document.allow_lambda_and_textract.json
}

data "aws_iam_policy_document" "allow_lambda_and_textract" {
    statement {
      principals {
        type = "Service"
        identifiers = ["textract.amazonaws.com"]
      }
      
      actions = [
        "s3:GetObject", 
        "s3:GetObjectAttributes"
      ]

      resources = [
        "arn:aws:s3:::${var.bucket_name}",
        "arn:aws:s3:::${var.bucket_name}/*"
      ]
    }
}

// Creating the directory structure in S3 that's part of the lambda function's logic.
resource "aws_s3_object" "object" {
    for_each = toset(["pdf_images/", "csv_data/"])
    bucket = var.bucket_name
    key    = each.value
    content = ""
    depends_on = [ aws_s3_bucket.textract_data_bucket ]
}

/*
-------------------------------
Lambda Function
-------------------------------
*/

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

// Creating the Lambda Function
resource "aws_lambda_function" "textract_lambda" {
  filename      = "lambda_function_payload.zip"
  function_name = "call-textract"
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda.output_base64sha256
  runtime = "python3.10"
  timeout = 300

  dead_letter_config {
    target_arn = aws_sns_topic.on_lambda_function_error.arn
  }

  tags = {
    project = var.project_name
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/python-scripts"
  output_path = "${path.module}/lambda_function_payload.zip"
}


// Permissions for SNS
resource "aws_iam_role_policy_attachment" "lambda_sns_publish_attachment" {
  role = aws_iam_role.iam_for_lambda.id
  policy_arn = aws_iam_policy.lambda_sns_publish.arn
}

resource "aws_iam_policy" "lambda_sns_publish" {
  name = "lambda_sns_publish_policy"
  policy = data.aws_iam_policy_document.lambda_sns_publish_policy.json
}

data "aws_iam_policy_document" "lambda_sns_publish_policy" {
    statement {
      effect = "Allow"
      actions = ["sns:Publish"]
      resources = [aws_sns_topic.on_lambda_function_error.arn]
    }
}


// Permissions for Textract
resource "aws_iam_role_policy_attachment" "lambda_textract_attachment" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.textract_policy.arn
}

resource "aws_iam_policy" "textract_policy" {
  name   = "lambda_textract_policy"
  policy = data.aws_iam_policy_document.lambda_textract_policy.json
}

data "aws_iam_policy_document" "lambda_textract_policy" {
  statement {
    effect = "Allow"
    actions = ["textract:*"]
    resources = ["*"]
  }
}


// Permissions for S3
resource "aws_iam_role_policy_attachment" "lambda_s3_attachment" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_s3_access_policy.arn
}

resource "aws_iam_policy" "lambda_s3_access_policy" {
  name   = "lambda_s3_access_policy"
  policy = data.aws_iam_policy_document.lambda_s3_policy.json
}

data "aws_iam_policy_document" "lambda_s3_policy" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectAttributes", 
      "s3:PutObject"
    ]

    resources = ["${aws_s3_bucket.textract_data_bucket.arn}/*"]
  }
}

resource "aws_lambda_permission" "allow_S3" {
    statement_id = "AllowExecutionFromS3"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.textract_lambda.function_name
    principal = "s3.amazonaws.com"
    source_arn = aws_s3_bucket.textract_data_bucket.arn
}

resource "aws_s3_bucket_notification" "aws_lambda_trigger" {
    bucket = aws_s3_bucket.textract_data_bucket.id
    lambda_function {
      lambda_function_arn = aws_lambda_function.textract_lambda.arn
      events = ["s3:ObjectCreated:*"]
      filter_prefix = "pdf_images/"
      filter_suffix = ".pdf"
    }
}


// Permission for CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs_attachment" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_policy" "lambda_logging" {
  name   = "lambda_logging_policy"
  policy = data.aws_iam_policy_document.lambda_logging_policy.json
}


data "aws_iam_policy_document" "lambda_logging_policy" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = ["arn:aws:logs:*:*:*"]
  }
}

/*
-------------------------------
SNS Topic
-------------------------------
*/

resource "aws_sns_topic" "on_lambda_function_error" {
    name = "on-lambda-textract-error"
    tags = {
        project = var.project_name
    }
}

resource "aws_sns_topic_subscription" "lambda_topic" {
    topic_arn = aws_sns_topic.on_lambda_function_error.arn
    protocol = "email"
    endpoint = var.email
}

variable "email" {
    default = "null"
    description = "The email of the person who should be notified on failure of the lambda function."
}