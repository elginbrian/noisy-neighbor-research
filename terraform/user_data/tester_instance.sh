#!/bin/bash
# Bootstrap Tester Instance (Ubuntu Server 22.04 LTS).
# Hasil: JRE, Apache JMeter (versi dikunci), dan Python untuk Skrip Otomasi Pengujian.
# Penanda selesai : /var/log/bootstrap-done
# Penanda gagal   : /var/log/bootstrap-failed
# Log lengkap     : /var/log/bootstrap.log
set -euxo pipefail
exec > >(tee -a /var/log/bootstrap.log) 2>&1
trap 'touch /var/log/bootstrap-failed' ERR

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

JMETER_VERSION="5.6.3"

# 1. Hentikan pembaruan otomatis latar belakang agar tidak mengganggu pembangkit beban & tidak mengunci apt
systemctl stop unattended-upgrades apt-daily.service apt-daily-upgrade.service 2>/dev/null || true
systemctl kill --kill-who=all unattended-upgrades 2>/dev/null || true
systemctl disable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer || true

# Tunggu pelepasan lock apt jika sempat dipegang oleh proses boot awal
while fuser /var/lib/dpkg/lock >/dev/null 2>&1 || fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do
  echo "Menunggu pelepasan lock apt oleh proses boot awal..."
  sleep 2
done

# 2. Paket dasar: JRE, Python, dan utilitas
apt-get update
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
  openjdk-17-jre-headless python3-pip unzip curl tmux

# 3. Apache JMeter (unduh via Fastly CDN resmi dengan fallback & timeout agar tidak hang)
cd /opt
JMETER_TAR="apache-jmeter-${JMETER_VERSION}.tgz"
MIRRORS=(
  "https://dlcdn.apache.org/jmeter/binaries/${JMETER_TAR}"
  "https://downloads.apache.org/jmeter/binaries/${JMETER_TAR}"
  "https://archive.apache.org/dist/jmeter/binaries/${JMETER_TAR}"
)

DOWNLOADED=0
for url in "${MIRRORS[@]}"; do
  echo "Mengunduh Apache JMeter dari $url ..."
  if curl -fL --connect-timeout 10 --speed-limit 150000 --speed-time 15 --retry 2 -o "$JMETER_TAR" "$url"; then
    DOWNLOADED=1
    echo "Unduhan Apache JMeter selesai."
    break
  else
    echo "Mirror $url lambat/gagal, mencoba mirror berikutnya..."
    rm -f "$JMETER_TAR"
  fi
done

if [ "$DOWNLOADED" -ne 1 ]; then
  echo "ERROR: Gagal mengunduh Apache JMeter dari seluruh mirror!" >&2
  exit 1
fi

tar -xzf "$JMETER_TAR"
rm -f "$JMETER_TAR"
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
