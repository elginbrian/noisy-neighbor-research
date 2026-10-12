# Victim Container

Web server korban berbasis Nginx ringan (`alpine`) yang melayani beban normal konstan (50 RPS) selama 60 detik penuh.

## Spesifikasi & Desain
- **Base Image**: `nginx:1.27-alpine`
- **Port**: 80
- **Access Log**: Dinonaktifkan (`access_log off;`) agar I/O disk murni menjadi *cross-resource side-effect* tanpa distorsi log web server.
- **Endpoint**:
  - `GET /`: Mengembalikan payload statis ringan.
  - `GET /health`: Endpoint pemeriksaan kesiapan probe.

## Build Image
```bash
docker build -t nn-victim:latest apps/victim/
```

## Menjalankan Container
Victim berjalan tanpa batasan cgroups dan tanpa restart:
```bash
docker run -d --name nn-victim --restart=no -p 80:80 nn-victim:latest
```
