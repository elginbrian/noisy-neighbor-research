resource "aws_instance" "target" {
  ami                    = data.aws_ami.ubuntu_2204.id
  instance_type          = var.target_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.nn.id]
  key_name               = aws_key_pair.main.key_name
  user_data              = file("${path.module}/user_data/target_instance.sh")
  user_data_replace_on_change = true

  credit_specification {
    cpu_credits = "unlimited"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_size_gb
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
  }

  tags = {
    Name = "nn-target-instance"
    Role = "target"
  }
}

resource "aws_instance" "tester" {
  ami                    = data.aws_ami.ubuntu_2204.id
  instance_type          = var.tester_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.nn.id]
  key_name               = aws_key_pair.main.key_name
  user_data              = file("${path.module}/user_data/tester_instance.sh")
  user_data_replace_on_change = true

  credit_specification {
    cpu_credits = "unlimited"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_size_gb
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
  }

  tags = {
    Name = "nn-tester-instance"
    Role = "tester"
  }
}
