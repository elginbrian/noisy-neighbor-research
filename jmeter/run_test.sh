#!/bin/bash
# ==============================================================================
# Skrip pembantu eksekusi Apache JMeter Non-GUI di Tester Instance.
# Sesuai Proposal Skripsi Bab 3.2.3, 3.4.3, dan 3.4.4.
# ==============================================================================
set -euo pipefail

TARGET_HOST="${1:-127.0.0.1}"
SESSION_ID="${2:-session_$(date +%s)}"
OUTPUT_DIR="${3:-results}"

mkdir -p "$OUTPUT_DIR"
JTL_FILE="$OUTPUT_DIR/jmeter_${SESSION_ID}.jtl"

echo "================================================================="
echo "[JMeter] Memulai injeksi beban non-GUI ke Target Instance: $TARGET_HOST"
echo "[JMeter] Sesi ID : $SESSION_ID"
echo "[JMeter] Output  : $JTL_FILE"
echo "================================================================="

# Optimasi alokasi heap Java untuk Tester Instance t3.medium (4 GB RAM)
export HEAP="-Xms1g -Xmx2g -XX:MaxMetaspaceSize=256m"

# Pastikan jmeter ada di PATH atau gunakan fallback /opt/jmeter/bin/jmeter
JMETER_CMD="jmeter"
if ! command -v jmeter &> /dev/null; then
    if [ -f "/opt/jmeter/bin/jmeter" ]; then
        JMETER_CMD="/opt/jmeter/bin/jmeter"
    else
        echo "[JMeter] Error: Perintah 'jmeter' tidak ditemukan!" >&2
        exit 1
    fi
fi

# Jalankan pengujian Non-GUI
$JMETER_CMD -n \
  -t "$(dirname "$0")/test_plan.jmx" \
  -l "$JTL_FILE" \
  -JTARGET_HOST="$TARGET_HOST" \
  -JTOTAL_DURATION_SEC=60 \
  -JBASELINE_DURATION_SEC=10 \
  -JINJECTION_DURATION_SEC=50 \
  -JVICTIM_RPM=3000.0 \
  -JAGGRESSOR_THREADS=50

echo "[JMeter] Eksekusi beban selesai."

# Ekstraksi dan kalkulasi metrik ke ringkasan JSON
python3 "$(dirname "$0")/parse_results.py" \
  --jtl "$JTL_FILE" \
  --session-id "$SESSION_ID" \
  --output-json "$OUTPUT_DIR/summary_jmeter_${SESSION_ID}.json"
