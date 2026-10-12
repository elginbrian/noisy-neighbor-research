#!/bin/bash
set -euo pipefail

APPS_DIR="/home/ubuntu/apps"
HASH_FILE="/home/ubuntu/.hash_apps"
VERIFIED_FLAG="/tmp/.nn_docker_verified"

NEED_BUILD=0
if ! docker image inspect nn-victim:latest >/dev/null 2>&1 || ! docker image inspect nn-aggressor:latest >/dev/null 2>&1; then
    NEED_BUILD=1
elif [ ! -f "$VERIFIED_FLAG" ] || [ -f "$HASH_FILE" -a "$HASH_FILE" -nt "$VERIFIED_FLAG" ]; then
    NEED_BUILD=1
fi

if [ "$NEED_BUILD" -eq 1 ]; then
    echo "Membangun container image nn-victim dan nn-aggressor..."
    docker build -t nn-victim:latest "$APPS_DIR/victim" >/dev/null
    docker build -t nn-aggressor:latest "$APPS_DIR/aggressor" >/dev/null
    echo "[OK] Docker images berhasil dibangun."

    # Smoke test kesiapan container (bersihkan jika ada container lama di port 80/8000)
    docker rm -f nn-victim nn-aggressor nn-victim-probe nn-aggressor-probe 2>/dev/null || true
    docker run -d --name nn-victim-probe -p 80:80 nn-victim:latest >/dev/null
    docker run -d --name nn-aggressor-probe -p 8000:8000 nn-aggressor:latest >/dev/null
    sleep 2
    curl -s -f http://localhost:80/health >/dev/null && echo "[OK] Victim container merespons /health."
    curl -s -f http://localhost:8000/health >/dev/null && echo "[OK] Aggressor container merespons /health."
    docker rm -f nn-victim-probe nn-aggressor-probe >/dev/null
    touch "$VERIFIED_FLAG"
else
    echo "[OK] Container image sudah tersedia dan terverifikasi (skip rebuild)."
fi
