# Skrip Pemantau Pengujian (Tracker)

Skrip pemantau berbasis Python yang beroperasi di latar belakang *Target Instance* untuk merekam metrik penggunaan sumber daya sistem dan intervensi cgroups v2 setiap 2 detik.

Rancangan mengikuti **Proposal Skripsi Bab 3.2.3 (Poin 2), Bab 3.3.2 (Tabel 3.3.1), Bab 3.4.3, dan Bab 3.4.4**.

---

## Struktur Modul

Kode dipecah menjadi modul-modul kecil dan terfokus:
- **`host.py`**: Mengambil metrik CPU & RAM host via `psutil`.
- **`disk.py`**: Mengambil metrik throughput (kB/s) dan latency (await, ms) via `iostat -x` dengan fallback `psutil`.
- **`cgroups.py`**: Menemukan path cgroups v2, membaca `cpu.stat`, `memory.events`, `memory.current`, serta memeriksa status OOM container via `docker inspect`.
- **`aggregator.py`**: Menghitung agregasi statistik (mean, min, P95) dan memisahkan fase baseline (0–10s) dari fase injeksi beban (10–60s).
- **`tracker.py`**: Main coordinator / CLI runner yang mengeksekusi loop sampling setiap interval detik.

---

## 1. Variabel Terikat yang Dipantau

| Sumber | Instrumen / Sumber Data | Metrik | Keterangan & Metode Agregasi |
|---|---|---|---|
| Host | `psutil.cpu_percent` | `host_cpu_pct` | Rata-rata selama fase injeksi (%) |
| Host | `psutil.virtual_memory` | `host_spare_mem_mb` | Nilai minimum selama fase injeksi (MB) |
| Host | `iostat -x` (`sysstat`) / psutil | `host_disk_throughput_kbps` | Kecepatan baca+tulis rata-rata fase injeksi (kB/s) |
| Host | `iostat -x` (`sysstat`) / psutil | `host_disk_await_ms` | Waktu tunggu I/O persentil ke-95 / P95 (ms) |
| Container | `/sys/fs/cgroup/.../cpu.stat` | `aggressor_nr_throttled` | Jumlah kumulatif kejadian CPU throttling |
| Container | `/sys/fs/cgroup/.../cpu.stat` | `aggressor_throttled_usec` | Total mikrodetik CPU di-throttle |
| Container | `/sys/fs/cgroup/.../memory.events` | `aggressor_oom_kill_count` | Jumlah kumulatif kejadian OOM Kill |
| Container | `docker inspect` (State.OOMKilled) | `aggressor_oom_killed` | Boolean (0 atau 1) beserta detik kejadiannya |
| Container | `/sys/fs/cgroup/.../memory.current`| `aggressor_mem_current_mb` | Penggunaan memori aktual container (MB) |

---

## 2. Cara Menjalankan

### Dependensi
Di Target Instance, paket `python3-psutil` dan `sysstat` sudah terinstal otomatis saat *bootstrap* melalui `target_instance.sh`.

```bash
# Menjalankan pemantauan untuk 1 sesi (default 60 detik, interval 2 detik):
python3 monitoring/tracker.py --session-id "cell_1_rep_1" --duration 60 --interval 2 --output-dir "results"
```

### Opsi Parameter
- `--session-id`: ID unik sesi pengujian (contoh: `cell_01_rep_01`).
- `--duration`: Total durasi pengujian dalam detik (default: `60.0`).
- `--interval`: Interval pencatatan data dalam detik (default: `2.0`).
- `--output-dir`: Direktori tujuan penyimpanan berkas hasil (default: `results`).
- `--container-aggressor`: Nama container aggressor (default: `nn-aggressor`).
- `--container-victim`: Nama container victim (default: `nn-victim`).

---

## 3. Berkas Keluaran

1. **`metrics_<session_id>.csv`**:
   Data *time-series* per 2 detik dari detik 0 hingga 60 yang berisi seluruh kolom metrik di atas.
2. **`summary_<session_id>.json`**:
   Ringkasan agregasi otomatis yang memisahkan **Fase Baseline (0–10s)** dan **Fase Injeksi (10–60s)** sesuai dengan rumus dan metode agregasi pada Bab 3.3.2 Proposal.
