resource "aws_security_group" "nn" {
  name        = "nn-sg"
  description = "Security Group penelitian noisy neighbor"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "nn-sg"
  }
}

# SSH hanya dari IP peneliti
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.nn.id
  description       = "SSH dari IP peneliti"
  cidr_ipv4         = var.allowed_ssh_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

# Seluruh lalu lintas internal antar node (JMeter ke container, SCP, dll.)
resource "aws_vpc_security_group_ingress_rule" "internal" {
  security_group_id            = aws_security_group.nn.id
  description                  = "Lalu lintas internal antar node"
  referenced_security_group_id = aws_security_group.nn.id
  ip_protocol                  = "-1"
}

# Keluar bebas (instalasi paket saat bootstrap)
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.nn.id
  description       = "Semua lalu lintas keluar"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
