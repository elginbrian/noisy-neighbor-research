#!/bin/bash
# Bootstrap Attacker Node (Ubuntu Server 22.04 LTS).
# Hasil: JRE, Apache JMeter (versi dikunci), dan Python untuk Skrip Otomasi Pengujian.
# Penanda selesai : /var/log/bootstrap-done
# Penanda gagal   : /var/log/bootstrap-failed
# Log lengkap     : /var/log/bootstrap.log
set -euxo pipefail
exec > >(tee -a /var/log/bootstrap.log) 2>&1
trap 'touch /var/log/bootstrap-failed' ERR

export DEBIAN_FRONTEND=noninteractive

JMETER_VERSION="5.6.3"

# 1. Hentikan pembaruan otomatis latar belakang agar tidak mengganggu pembangkit beban
systemctl disable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer || true

# 2. Paket dasar: JRE (prasyarat JMeter), Python, dan utilitas
apt-get update
apt-get install -y openjdk-17-jre-headless python3-pip unzip curl tmux

# 3. Apache JMeter (versi dikunci demi reprodusibilitas, Bab 3.2.3)
cd /opt
curl -fsSLO "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz"
tar -xzf "apache-jmeter-${JMETER_VERSION}.tgz"
rm "apache-jmeter-${JMETER_VERSION}.tgz"
ln -sfn "/opt/apache-jmeter-${JMETER_VERSION}" /opt/jmeter
ln -sfn /opt/jmeter/bin/jmeter /usr/local/bin/jmeter

# 4. Direktori kerja untuk skrip otomasi dan hasil sesi
install -d -o ubuntu -g ubuntu /home/ubuntu/results /home/ubuntu/automation /home/ubuntu/jmeter

# 5. Verifikasi
jmeter --version
java -version
python3 --version

{
  echo "jmeter=${JMETER_VERSION}"
  echo "java=$(java -version 2>&1 | head -n 1)"
  echo "python=$(python3 --version)"
} > /var/log/bootstrap-versions.txt

touch /var/log/bootstrap-done
