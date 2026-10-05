data "aws_availability_zones" "available" {
  state = "available"
}

# AMI Ubuntu Server 22.04 LTS resmi dari Canonical.
# Catatan: data source ini dibaca dari AWS saat `terraform plan`/`apply`.
# Untuk reprodusibilitas (Bab 3.2.3), setelah AMI terpilih, kunci ke satu AMI ID.
data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
