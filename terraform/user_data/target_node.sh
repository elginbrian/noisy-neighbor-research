#!/bin/bash
# Bootstrap Target Node (Ubuntu Server 22.04 LTS).
# Hasil: swap nonaktif, Docker Engine 27.x (cgroup driver systemd) di atas cgroups v2,
# sysstat (iostat) dan psutil untuk Skrip Pemantau Pengujian.
# Penanda selesai : /var/log/bootstrap-done
# Penanda gagal   : /var/log/bootstrap-failed
# Log lengkap     : /var/log/bootstrap.log
set -euxo pipefail
exec > >(tee -a /var/log/bootstrap.log) 2>&1
trap 'touch /var/log/bootstrap-failed' ERR

export DEBIAN_FRONTEND=noninteractive

# 1. Nonaktifkan swap permanen agar perilaku OOM Killer deterministik (Bab 3.4.4.E)
swapoff -a
sed -i '/\sswap\s/d' /etc/fstab

# 2. Hentikan pembaruan otomatis latar belakang agar tidak menambah beban CPU/disk
#    selama eksperimen (menjaga kondisi testbed terkendali)
systemctl disable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer || true

# 3. Paket dasar: sysstat (iostat) dan psutil untuk Skrip Pemantau Pengujian
apt-get update
apt-get install -y ca-certificates curl gnupg sysstat python3-pip python3-psutil

# 4. Repositori resmi Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update

# 5. Docker Engine seri 27.x (versi dikunci demi reprodusibilitas, Bab 3.2.3)
DOCKER_VERSION=$(apt-cache madison docker-ce | awk '{print $3}' | grep '^5:27\.' | head -n 1)
test -n "$DOCKER_VERSION"
apt-get install -y \
  docker-ce="$DOCKER_VERSION" \
  docker-ce-cli="$DOCKER_VERSION" \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
apt-mark hold docker-ce docker-ce-cli

# 6. Cgroup driver systemd (cgroups v2 sudah default pada Ubuntu 22.04)
cat > /etc/docker/daemon.json <<'EOF'
{
  "exec-opts": ["native.cgroupdriver=systemd"]
}
EOF
systemctl enable docker
systemctl restart docker

# 7. Izinkan user ubuntu menjalankan docker tanpa sudo
usermod -aG docker ubuntu

# 8. Verifikasi lingkungan; gagal bila tidak sesuai desain penelitian
test "$(stat -fc %T /sys/fs/cgroup)" = "cgroup2fs"
test "$(docker info --format '{{.CgroupVersion}}')" = "2"
test "$(docker info --format '{{.CgroupDriver}}')" = "systemd"
test "$(swapon --show | wc -l)" = "0"

{
  echo "docker=$(docker --version)"
  echo "cgroup_fs=$(stat -fc %T /sys/fs/cgroup)"
  echo "kernel=$(uname -r)"
} > /var/log/bootstrap-versions.txt

touch /var/log/bootstrap-done
