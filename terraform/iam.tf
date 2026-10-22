# IAM role Tester Instance untuk pemulihan otomatis Target Instance yang hang.
# Izin dibatasi: hanya reboot Target Instance dan membaca status instance.
resource "aws_iam_role" "tester" {
  name = "nn-tester-recovery-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "tester_recovery" {
  name = "nn-tester-recovery-policy"
  role = aws_iam_role.tester.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ec2:RebootInstances"]
        Resource = aws_instance.target.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:DescribeInstanceStatus"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "tester" {
  name = "nn-tester-recovery-profile"
  role = aws_iam_role.tester.name
}
