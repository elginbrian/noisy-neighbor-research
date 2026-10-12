#!/bin/bash
set -euo pipefail

TARGET_PRIVATE_IP="${1:-10.0.1.10}"

# 1. Cek versi Apache JMeter
if /opt/jmeter/bin/jmeter -v >/dev/null 2>&1; then
    echo "[OK] Apache JMeter terinstalasi dan siap digunakan."
else
    echo "[ERROR] Apache JMeter tidak ditemukan di /opt/jmeter/bin/jmeter!" >&2
    exit 1
fi

# 2. Cek konektivitas SSH privat ke Target Instance
if ssh -i ~/.ssh/noisy-neighbor -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=5 ubuntu@"$TARGET_PRIVATE_IP" "docker --version" >/dev/null 2>&1; then
    echo "[OK] Tester terhubung ke Target via IP privat: $TARGET_PRIVATE_IP"
else
    echo "[ERROR] Tester gagal menghubungi Target di IP privat $TARGET_PRIVATE_IP!" >&2
    exit 1
fi

# 3. Pastikan direktori results dan Dashboard Web aktif di port 8080
mkdir -p /home/ubuntu/results
if curl -s -f http://localhost:8080/ >/dev/null 2>&1 || ss -tulpn 2>/dev/null | grep -q ":8080 "; then
    echo "[OK] Dashboard Web sudah aktif di port 8080."
else
    nohup python3 /home/ubuntu/orchestrator/dashboard.py --port 8080 --results-dir /home/ubuntu/results </dev/null >/home/ubuntu/dashboard.log 2>&1 &
    disown 2>/dev/null || true
    sleep 1
    if curl -s -f http://localhost:8080/ >/dev/null 2>&1; then
        echo "[OK] Dashboard Web berhasil dijalankan di port 8080."
    else
        echo "[WARN] Dashboard Web sedang memulai..."
    fi
fi
