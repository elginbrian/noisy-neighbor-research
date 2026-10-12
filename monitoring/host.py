"""Pembacaan metrik penggunaan CPU dan Memori Host."""

from typing import Tuple

import psutil


class HostReader:
    def __init__(self):
        # Inisialisasi awal agar pembacaan cpu_percent berikutnya tidak bernilai 0.0
        psutil.cpu_percent(interval=None)

    def get_metrics(self) -> Tuple[float, float]:
        """
        Mengambil metrik Host:
        Mengembalikan tuple: (host_cpu_pct, host_spare_mem_mb).
        """
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        spare_mem_mb = round(mem.available / (1024 * 1024), 2)
        return cpu_pct, spare_mem_mb
