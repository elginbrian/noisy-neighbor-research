# Skrip Otomasi Pengujian / Orchestrator (Pilar 4)

Skrip orkestrator pengujian berbasis Python yang berjalan di *Tester Instance* untuk mengendalikan seluruh siklus pengujian secara otomatis tanpa intervensi manual.

Rancangan mengikuti **Proposal Skripsi Bab 3.2.3 (Poin 3), Bab 3.3.4 (Tabel 3.3.2), dan Bab 3.4.4**.

---

## 1. Struktur Modul

Kode dipecah menjadi modul-modul kecil yang modular dan terfokus:
- **`matrix.py`**: Definisi 16 sel matriks pengujian (Tabel 3.3.2) dan generator rencana sesi (80 sesi acak).
- **`ssh_client.py`**: Abstraksi koneksi SSH dan pengunduhan SCP ke Target Instance.
- **`verifier.py`**: Verifikasi limit cgroups v2 (`cpu.max`, `memory.max`, dan memastikan `io.max` kosong) sebelum injeksi beban dimulai (Bab 3.4.4.D).
- **`session_runner.py`**: Eksekusi siklus 1 sesi (Reset container $\rightarrow$ Drop cache $\rightarrow$ Run container $\rightarrow$ Probe kesiapan $\rightarrow$ Jalankan Tracker & JMeter $\rightarrow$ Tarik hasil via SCP).
- **`dashboard.py`**: Server dashboard web ringan berbasis Python stdlib (port 8080) untuk memantau progres real-time dan mengunduh berkas arsip ZIP seluruh hasil pengujian.
- **`runner.py`**: Entry point CLI utama yang mengorkestrasi eksekusi sesi berurutan dengan jeda idle 30 detik (Bab 3.4.4.C).

---

## 2. Alur Eksekusi per Sesi (Bab 3.4.4 & Gambar 3.4.2)

1. **Reset Container**: Menghapus container lama di Target Instance (`docker rm -f nn-aggressor nn-victim`).
2. **Pembersihan Page Cache**: Mengeksekusi `sync && echo 3 > /proc/sys/vm/drop_caches` di host Target Instance.
3. **Deploy Container**: Menjalankan Victim (port 80) dan Aggressor (port 8000) dengan opsi `--cpus` dan `--memory` sesuai sel.
4. **Probe Kesiapan**: Memeriksa HTTP `GET /health` di port 80 dan 8000 sampai merespons 200 OK.
5. **Verifikasi Limit Cgroups**: Membaca filesystem `/sys/fs/cgroup/` untuk memastikan konfigurasi limit aktif dengan benar.
6. **Mulai Pemantau**: Menjalankan `monitoring/tracker.py` di Target Instance.
7. **Injeksi Beban JMeter**: Menjalankan JMeter non-GUI di Tester Instance (10 detik baseline 50 RPS ke Victim, lalu 50 detik paralel flood ke Aggressor).
8. **Tarik Log via SCP**: Mengunduh `metrics_<id>.csv` dan `summary_<id>.json` dari Target Instance.
9. **Kompilasi Hasil**: Menjalankan `parse_results.py` untuk mengurai `.jtl` JMeter dan menggabungkan ringkasan ke `combined_<id>.json`.
10. **Jeda Idle**: Menunggu 30 detik agar penggunaan CPU dan sisa memori host kembali ke kondisi normal (*steady state*) sebelum sesi berikutnya dimulai.

---

## 3. Cara Menjalankan

### A. Uji Coba Urutan Sesi (Dry Run):
Melihat urutan acak rencana 80 sesi tanpa mengeksekusi apa pun:
```bash
python3 orchestrator/runner.py --target-ip 10.0.1.X --mode full --dry-run
```

### B. Mode Pilot Study (16 Sel x 1 Replikasi):
```bash
python3 orchestrator/runner.py --target-ip 10.0.1.X --mode pilot
```

### C. Mode Single Cell (Menguji 1 Sel Spesifik):
Contoh menguji Sel 1 (Kondisi Kontrol - Tanpa Limit):
```bash
python3 orchestrator/runner.py --target-ip 10.0.1.X --mode single --cell 1
```

Contoh menguji Sel 16 (Limit Paling Ketat: 0.5 vCPU, 256 MB):
```bash
python3 orchestrator/runner.py --target-ip 10.0.1.X --mode single --cell 16
```

### D. Mode Full Experiment (80 Sesi Penuh):
```bash
python3 orchestrator/runner.py --target-ip 10.0.1.X --mode full
```

---

## 4. Dashboard Web & Pengunduhan Hasil (Port 8080)

Saat `runner.py` berjalan, server dashboard otomatis aktif di latar belakang pada port 8080:
- **Akses Dashboard**: Buka `http://<tester_public_ip>:8080` di browser.
- **Fitur Dashboard**:
  - Progres persentase (%) dan indikator sesi berjalan.
  - Detail status tahapan eksekusi per sesi (*reset container, drop cache, run JMeter, idle*).
  - Tabel hasil metrik sesi yang telah selesai (*P95 Latency, Uptime %, Host CPU %, OOM Kill status*).
  - Tombol **Unduh Seluruh Hasil (.zip)** langsung dari browser (`/api/download/all`).
- **Mode Standalone (Tanpa Menjalankan Uji Ulang)**:
  Jika ingin membuka web server hanya untuk melihat hasil lama atau mengunduh zip:
  ```bash
  python3 orchestrator/dashboard.py --port 8080 --results-dir results
  ```

