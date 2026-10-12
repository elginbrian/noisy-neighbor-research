import hashlib
import os
import threading
import time

from fastapi import FastAPI

# Parameter beban kerja dikonfigurasi melalui Environment Variables
CPU_ITERATIONS = int(os.getenv("CPU_ITERATIONS", "100"))
MEM_MB_PER_REQ = int(os.getenv("MEM_MB_PER_REQ", "4"))
MEM_TARGET_MB = int(os.getenv("MEM_TARGET_MB", "640"))

MB = 1024 * 1024
BLOCK = os.urandom(64 * 1024)   # Blok acak tetap 64 KiB, dibuat sekali saat startup
HELD = []                       # List global untuk menahan blok memori (mencegah GC)
held_mb = 0
lock = threading.Lock()
started_at = time.time()

# Matikan docs Swagger bawaan untuk meminimalkan alokasi memori saat container idle
app = FastAPI(title="Aggressor Service", docs_url=None, redoc_url=None, openapi_url=None)


def burn_cpu(iterations: int) -> str:
    """Komputasi SHA-256 intensif CPU (melepas GIL Python pada blok besar)."""
    h = hashlib.sha256()
    for _ in range(iterations):
        h.update(BLOCK)
    return h.hexdigest()


def grab_memory() -> bool:
    """Alokasi dan penulisan memori non-nol untuk memaksa OS mengalokasikan RSS fisik."""
    global held_mb
    with lock:
        if held_mb + MEM_MB_PER_REQ > MEM_TARGET_MB:
            return False
        held_mb += MEM_MB_PER_REQ
    # bytearray dengan data non-nol memastikan alokasi bukan 'lazy' (RSS riil bertambah)
    HELD.append(bytearray(b"\xa5") * (MEM_MB_PER_REQ * MB))
    return True


@app.get("/health")
def health():
    """Endpoint kesiapan (readiness probe) yang dipanggil sebelum sesi pengujian."""
    return {"status": "ok"}


@app.get("/stress")
def stress():
    """
    Endpoint pemicu noisy neighbor:
    1. Menambah alokasi memori fisik jika target belum tercapai
    2. Menjalankan komputasi SHA-256 fixed-work
    Handler sinkron (def) agar FastAPI menjalankannya di worker thread terpisah.
    """
    grabbed = grab_memory()
    burn_cpu(CPU_ITERATIONS)
    return {"mem_held_mb": held_mb, "target_reached": not grabbed}


@app.get("/stats")
def stats():
    """Melaporkan status memori yang ditahan untuk verifikasi saat pilot study."""
    return {
        "mem_held_mb": held_mb,
        "target_mb": MEM_TARGET_MB,
        "uptime_s": round(time.time() - started_at, 1)
    }
