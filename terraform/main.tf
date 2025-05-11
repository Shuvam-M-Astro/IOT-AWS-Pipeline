provider "aws" {
  region = "eu-central-1"
}

resource "aws_s3_bucket" "iot_data" {
  bucket = "iot-sensor-data-bucket"
  force_destroy = true
}

resource "aws_kinesis_stream" "iot_stream" {
  name        = "iot-sensor-stream"
  shard_count = 1
}

resource "aws_iam_role" "firehose_role" {
  name = "firehose_delivery_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "firehose.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "firehose_policy" {
  role = aws_iam_role.firehose_role.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetBucketLocation"
        ],
        Resource = "${aws_s3_bucket.iot_data.arn}/*"
      }
    ]
  })
}

resource "aws_kinesis_firehose_delivery_stream" "iot_firehose" {
  name        = "iot-delivery-stream"
  destination = "s3"

  s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = aws_s3_bucket.iot_data.arn
    prefix     = "sensor_data/"
    buffering_size = 5
    buffering_interval = 60
    compression_format = "GZIP"
  }
}
