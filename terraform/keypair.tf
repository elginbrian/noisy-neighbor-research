# Key pair dibuat lokal terlebih dahulu (hanya public key yang diunggah ke AWS):
#   ssh-keygen -t ed25519 -f ~/.ssh/noisy-neighbor
resource "aws_key_pair" "main" {
  key_name   = "nn-key"
  public_key = file(pathexpand(var.public_key_path))
}
