output "target_public_ip" {
  description = "IP publik Target Node (untuk SSH dari laptop)"
  value       = aws_instance.target.public_ip
}

output "target_private_ip" {
  description = "IP privat Target Node (sasaran JMeter dan SCP antar-node)"
  value       = aws_instance.target.private_ip
}

output "attacker_public_ip" {
  description = "IP publik Attacker Node (untuk SSH dari laptop)"
  value       = aws_instance.attacker.public_ip
}

output "attacker_private_ip" {
  description = "IP privat Attacker Node"
  value       = aws_instance.attacker.private_ip
}

output "ssh_target" {
  description = "Perintah SSH ke Target Node"
  value       = "ssh -i ~/.ssh/noisy-neighbor ubuntu@${aws_instance.target.public_ip}"
}

output "ssh_attacker" {
  description = "Perintah SSH ke Attacker Node"
  value       = "ssh -i ~/.ssh/noisy-neighbor ubuntu@${aws_instance.attacker.public_ip}"
}
