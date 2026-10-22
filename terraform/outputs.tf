output "target_public_ip" {
  description = "IP publik Target Instance (untuk SSH dari laptop)"
  value       = aws_instance.target.public_ip
}

output "target_private_ip" {
  description = "IP privat Target Instance (sasaran JMeter dan SCP antar-instance)"
  value       = aws_instance.target.private_ip
}

output "target_instance_id" {
  description = "ID EC2 Target Instance (untuk pemulihan otomatis)"
  value       = aws_instance.target.id
}

output "aws_region" {
  description = "Region AWS infrastruktur"
  value       = var.region
}

output "tester_public_ip" {
  description = "IP publik Tester Instance (untuk SSH dari laptop)"
  value       = aws_instance.tester.public_ip
}

output "tester_private_ip" {
  description = "IP privat Tester Instance"
  value       = aws_instance.tester.private_ip
}

output "ssh_target" {
  description = "Perintah SSH ke Target Instance"
  value       = "ssh -i ~/.ssh/noisy-neighbor ubuntu@${aws_instance.target.public_ip}"
}

output "ssh_tester" {
  description = "Perintah SSH ke Tester Instance"
  value       = "ssh -i ~/.ssh/noisy-neighbor ubuntu@${aws_instance.tester.public_ip}"
}

output "dashboard_url" {
  description = "URL Dashboard Web Pemantauan Eksperimen & Pengunduhan Hasil"
  value       = "http://${aws_instance.tester.public_ip}:8080"
}

# ==============================================================
# Alias Kompatibilitas Mundur (Backward Compatibility)
# ==============================================================
output "attacker_public_ip" {
  description = "Alias untuk tester_public_ip"
  value       = aws_instance.tester.public_ip
}

output "attacker_private_ip" {
  description = "Alias untuk tester_private_ip"
  value       = aws_instance.tester.private_ip
}

output "ssh_attacker" {
  description = "Alias untuk ssh_tester"
  value       = "ssh -i ~/.ssh/noisy-neighbor ubuntu@${aws_instance.tester.public_ip}"
}
