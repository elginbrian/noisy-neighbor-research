variable "region" {
  description = "Region AWS tempat infrastruktur dibuat"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "Blok CIDR untuk VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "Blok CIDR untuk subnet publik"
  type        = string
  default     = "10.0.1.0/24"
}

variable "allowed_ssh_cidr" {
  description = "IP publik peneliti yang boleh SSH, format x.x.x.x/32"
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0)) && var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "Gunakan CIDR yang valid dan jangan membuka SSH ke seluruh internet (0.0.0.0/0)."
  }
}

variable "public_key_path" {
  description = "Path file public key SSH (.pub)"
  type        = string
  default     = "~/.ssh/noisy-neighbor.pub"
}

variable "target_instance_type" {
  description = "Tipe instance Target Node (Tabel 3.2.1)"
  type        = string
  default     = "t2.small"
}

variable "attacker_instance_type" {
  description = "Tipe instance Attacker Node (Tabel 3.2.1)"
  type        = string
  default     = "t3.medium"
}

variable "volume_size_gb" {
  description = "Ukuran root volume gp3 per instance (GB)"
  type        = number
  default     = 20
}

variable "budget_limit_usd" {
  description = "Batas anggaran bulanan (USD) sebelum notifikasi dikirim"
  type        = number
  default     = 5
}

variable "budget_email" {
  description = "Alamat email penerima notifikasi AWS Budget"
  type        = string
}
