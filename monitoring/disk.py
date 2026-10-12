"""Pembacaan metrik Host Disk I/O Throughput dan Latency."""

import shutil
import subprocess
import time
from typing import Tuple

import psutil


class DiskReader:
    def __init__(self):
        self.has_iostat = shutil.which("iostat") is not None
        self.prev_disk_io = psutil.disk_io_counters()
        self.prev_time = time.time()

    def get_metrics(self) -> Tuple[float, float, float, float]:
        """
        Mengambil metrik Disk I/O:
        Mengembalikan tuple: (read_kbps, write_kbps, throughput_kbps, await_ms).
        Mengutamakan utilitas 'iostat -x' (dari sysstat) sesuai Bab 3.2.3.
        """
        if self.has_iostat:
            metrics = self._read_iostat()
            if metrics is not None:
                return metrics

        return self._read_psutil_fallback()

    def _read_iostat(self) -> Tuple[float, float, float, float]:
        """Mengeksekusi dan mem-parsing output 'iostat -x -k 1 2'."""
        try:
            # Laporan kedua dari '1 2' memberikan rata-rata 1 detik terakhir
            res = subprocess.run(
                ["iostat", "-x", "-k", "1", "2"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                reports = res.stdout.strip().split("avg-cpu:")
                target_report = reports[2] if len(reports) >= 3 else reports[-1]

                lines = target_report.strip().split("\n")
                header = []
                for line in lines:
                    tokens = line.split()
                    if not tokens:
                        continue
                    if "Device" in tokens:
                        header = tokens
                    elif header and (tokens[0].startswith("nvme") or tokens[0].startswith("xvd") or tokens[0].startswith("sd")):
                        col = dict(zip(header, tokens))
                        rkbs = float(col.get("rkB/s", col.get("rKB/s", 0.0)))
                        wkbs = float(col.get("wkB/s", col.get("wKB/s", 0.0)))
                        await_ms = float(col.get("await", col.get("r_await", 0.0)))
                        return rkbs, wkbs, rkbs + wkbs, await_ms
        except Exception:
            pass
        return None

    def _read_psutil_fallback(self) -> Tuple[float, float, float, float]:
        """Fallback membaca /proc/diskstats melalui psutil jika iostat tidak ada."""
        now = time.time()
        disk_io = psutil.disk_io_counters()
        if not disk_io or not self.prev_disk_io or self.prev_time <= 0:
            self.prev_disk_io = disk_io
            self.prev_time = now
            return 0.0, 0.0, 0.0, 0.0

        dt = max(now - self.prev_time, 0.001)

        read_bytes = disk_io.read_bytes - self.prev_disk_io.read_bytes
        write_bytes = disk_io.write_bytes - self.prev_disk_io.write_bytes
        read_kbps = round((read_bytes / 1024.0) / dt, 2)
        write_kbps = round((write_bytes / 1024.0) / dt, 2)
        throughput_kbps = round(read_kbps + write_kbps, 2)

        read_count = disk_io.read_count - self.prev_disk_io.read_count
        write_count = disk_io.write_count - self.prev_disk_io.write_count
        total_ios = read_count + write_count

        read_time_ms = disk_io.read_time - self.prev_disk_io.read_time
        write_time_ms = disk_io.write_time - self.prev_disk_io.write_time
        total_time_ms = read_time_ms + write_time_ms

        await_ms = round(total_time_ms / total_ios, 2) if total_ios > 0 else 0.0

        self.prev_disk_io = disk_io
        self.prev_time = now

        return read_kbps, write_kbps, throughput_kbps, await_ms
