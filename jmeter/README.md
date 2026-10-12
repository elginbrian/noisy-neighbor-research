# Apache JMeter Test Plan (Pilar 3)

Rancangan rencana pengujian Apache JMeter 5.6.3 untuk menghasilkan beban terukur sesuai **Proposal Skripsi Bab 3.2.3, Bab 3.3.2 (Tabel 3.3.1), dan Bab 3.4.3**.

---

## 1. Arsitektur Beban (Dua Fase Berurutan)

Setiap sesi pengujian berlangsung selama **60 detik**:

```
Detik 0 ----------------- 10 ----------------------------------- 60
[Fase 1: Baseline (10s)    ] [Fase 2: Injeksi Beban (50s)           ]
- Victim: 50 RPS            - Victim: 50 RPS (tetap konstan)
- Aggressor: Diam (idle)    - Aggressor: HTTP Request Flood (/stress)
```

1. **Victim Thread Group**:
   - Berjalan dari detik 0 hingga 60 (`TOTAL_DURATION_SEC = 60`).
   - Laju konstan: **50 RPS** (`VICTIM_RPM = 3000.0` requests per menit).
   - Target: `http://${TARGET_HOST}:80/` (Nginx container).
   - Mengukur: **Victim Latency (P95)** dan **Victim Uptime (%)**.
2. **Aggressor Thread Group**:
   - Ditunda 10 detik (`BASELINE_DURATION_SEC = 10`), baru aktif pada detik 10 hingga 60 (`INJECTION_DURATION_SEC = 50`).
   - Laju beban: Konkurensi 50 thread HTTP flood (`AGGRESSOR_THREADS = 50`).
   - Target: `http://${TARGET_HOST}:8000/stress` (FastAPI container).
   - Menyerap CPU dan memicu peningkatan physical RSS host.

---

## 2. Berkas dalam Folder Ini

- **`test_plan.jmx`**: Berkas XML definisi test plan Apache JMeter 5.6.3.
- **`run_test.sh`**: Skrip bash untuk menjalankan JMeter dalam mode *non-GUI* di Tester Instance dengan alokasi heap JVM optimal.
- **`reader.py`**: Pembaca berkas mentah `.jtl` (CSV/TSV) dan penormalisasi waktu relatif.
- **`stats.py`**: Fungsi pembantu kalkulasi statistik (`p95`, `mean`).
- **`calculator.py`**: Perhitungan metrik Victim (Uptime %, Latency P95, Waktu Tanggap Gangguan Rumus 3.1) dan Aggressor flood.
- **`parse_results.py`**: CLI coordinator untuk mengekstrak data dari berkas `.jtl` ke `summary_jmeter_<session_id>.json`.

---

## 3. Cara Menjalankan

### Melalui Skrip Bash (di Tester Instance):
```bash
./jmeter/run_test.sh <TARGET_PRIVATE_IP> "cell_01_rep_01" "results"
```

### Melalui Perintah JMeter Langsung (Non-GUI Mode):
```bash
jmeter -n \
  -t jmeter/test_plan.jmx \
  -l results/jmeter_session_01.jtl \
  -JTARGET_HOST=10.0.1.x \
  -JTOTAL_DURATION_SEC=60 \
  -JBASELINE_DURATION_SEC=10 \
  -JINJECTION_DURATION_SEC=50 \
  -JVICTIM_RPM=3000.0 \
  -JAGGRESSOR_THREADS=50
```

### Mengurai Hasil `.jtl` ke Ringkasan JSON:
```bash
python3 jmeter/parse_results.py \
  --jtl results/jmeter_session_01.jtl \
  --session-id "cell_01_rep_01" \
  --threshold-ms 1000.0
```
