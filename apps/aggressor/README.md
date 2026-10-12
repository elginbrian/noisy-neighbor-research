# Aggressor Container

Container pemicu fenomena *noisy neighbor* pada Target Instance berbasis Python FastAPI dan Uvicorn.

## Spesifikasi & Desain
- **Framework**: FastAPI (single-worker via Uvicorn, synchronous handler agar dijalankan di threadpool).
- **Endpoint**:
  - `GET /health`: Pemeriksaan kesiapan sebelum sesi pengujian.
  - `GET /stress`: Menahan blok memori non-nol (`bytearray`) untuk menaikkan RSS + komputasi SHA-256 CPU-bound.
  - `GET /stats`: Melaporkan total memori yang ditahan dan *uptime*.
- **Konfigurasi Beban (Environment Variables)**:
  - `CPU_ITERATIONS`: Jumlah hashing SHA-256 64 KiB per request (default: `100`).
  - `MEM_MB_PER_REQ`: Alokasi memori fisik per request (default: `4` MB).
  - `MEM_TARGET_MB`: Plafon alokasi memori sebelum berhenti menambah (default: `640` MB).

## Build Image
```bash
docker build -t nn-aggressor:latest apps/aggressor/
```

## Menjalankan Container
Sesuai skenario pengujian, container dijalankan tanpa restart otomatis (`--restart=no`) dan dengan limit cgroups v2 yang diinginkan:

```bash
# Contoh Sel 1 (Kondisi Kontrol - Tanpa Limit):
docker run -d --name nn-aggressor --restart=no -p 8000:8000 nn-aggressor:latest

# Contoh Sel 8 (CPU 75% / 1.5 vCPU, Memori 256 MB):
docker run -d --name nn-aggressor --restart=no --cpus=1.5 --memory=256m -p 8000:8000 nn-aggressor:latest
```
