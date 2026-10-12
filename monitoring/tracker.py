#!/usr/bin/env python3
"""
Skrip Pemantau Pengujian (Tracker Script) pada Target Instance.
Sesuai Proposal Skripsi Bab 3.2.3, 3.3.2, 3.4.3, dan 3.4.4.

Orkestrator pemantauan berkala yang mengoordinasikan modul:
- host.py      : Metrik CPU & Memory Host via psutil
- disk.py      : Metrik Disk I/O Throughput & Latency via iostat -x / psutil
- cgroups.py   : Metrik cgroups v2 (cpu.stat, memory.events) & status OOM
- aggregator.py: Agregasi metrik baseline vs injeksi beban (Tabel 3.3.1)
"""

import argparse
import csv
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Dukung eksekusi langsung (python tracker.py) maupun eksekusi modul (-m monitoring.tracker)
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from aggregator import calculate_aggregates
from cgroups import CgroupReader
from disk import DiskReader
from host import HostReader


class SystemTracker:
    def __init__(
        self,
        session_id: str,
        duration: float = 60.0,
        interval: float = 2.0,
        output_dir: str = "results",
        container_aggressor: str = "nn-aggressor",
        container_victim: str = "nn-victim",
    ):
        self.session_id = session_id
        self.duration = duration
        self.interval = interval
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.running = True
        self.start_time: float = 0.0
        self.samples: List[Dict] = []

        # Inisialisasi pembaca metrik termodularisasi
        self.host_reader = HostReader()
        self.disk_reader = DiskReader()
        self.cgroup_reader = CgroupReader(container_name=container_aggressor)

    def setup_signals(self):
        """Menangkap sinyal interupsi agar data tetap tersimpan sebelum proses ditutup."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        print(f"\n[Tracker] Sinyal {signum} diterima. Menyimpan data sebelum berhenti...", file=sys.stderr)
        self.running = False

    def take_sample(self, elapsed: float) -> Dict:
        """Mengambil satu baris sampel data metrik host dan container."""
        iso_time = datetime.now(timezone.utc).isoformat()
        host_cpu, host_spare_mem = self.host_reader.get_metrics()
        read_kbps, write_kbps, tp_kbps, await_ms = self.disk_reader.get_metrics()
        cg = self.cgroup_reader.get_metrics(self.start_time)

        return {
            "elapsed_s": round(elapsed, 2),
            "timestamp": iso_time,
            "host_cpu_pct": host_cpu,
            "host_spare_mem_mb": host_spare_mem,
            "host_disk_read_kbps": read_kbps,
            "host_disk_write_kbps": write_kbps,
            "host_disk_throughput_kbps": tp_kbps,
            "host_disk_await_ms": await_ms,
            "aggressor_cpu_usage_usec": cg["aggressor_cpu_usage_usec"],
            "aggressor_nr_throttled": cg["aggressor_nr_throttled"],
            "aggressor_throttled_usec": cg["aggressor_throttled_usec"],
            "aggressor_mem_current_mb": cg["aggressor_mem_current_mb"],
            "aggressor_oom_kill_count": cg["aggressor_oom_kill_count"],
            "aggressor_oom_killed": cg["aggressor_oom_killed"],
            "aggressor_oom_kill_second": cg["aggressor_oom_kill_second"],
        }

    def run(self):
        """Loop pencatatan berkala setiap interval detik."""
        self.setup_signals()
        self.start_time = time.time()
        print(f"[Tracker] Memulai pemantauan sesi '{self.session_id}' (durasi: {self.duration}s, interval: {self.interval}s)...")

        elapsed = 0.0
        while self.running and elapsed <= self.duration:
            loop_start = time.time()
            elapsed = loop_start - self.start_time

            self.samples.append(self.take_sample(elapsed))

            next_target = self.start_time + (len(self.samples) * self.interval)
            sleep_sec = next_target - time.time()
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        self.save_results()

    def save_results(self):
        """Menyimpan berkas CSV time-series dan berkas ringkasan JSON."""
        csv_file = self.output_dir / f"metrics_{self.session_id}.csv"
        json_file = self.output_dir / f"summary_{self.session_id}.json"

        if not self.samples:
            print("[Tracker] Tidak ada data sampel yang tercatat.", file=sys.stderr)
            return

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.samples[0].keys()))
            writer.writeheader()
            writer.writerows(self.samples)
        print(f"[Tracker] CSV tersimpan: {csv_file}")

        summary = calculate_aggregates(self.samples, self.session_id, self.cgroup_reader.latched_stats)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"[Tracker] Ringkasan JSON tersimpan: {json_file}")


def main():
    parser = argparse.ArgumentParser(description="Skrip Pemantau Pengujian (Target Instance)")
    parser.add_argument("--session-id", default=f"session_{int(time.time())}", help="Identifier unik sesi pengujian")
    parser.add_argument("--duration", type=float, default=60.0, help="Durasi sesi dalam detik (default: 60)")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval sampling dalam detik (default: 2.0)")
    parser.add_argument("--output-dir", default="results", help="Direktori penyimpanan berkas hasil")
    parser.add_argument("--container-aggressor", default="nn-aggressor", help="Nama container aggressor")
    parser.add_argument("--container-victim", default="nn-victim", help="Nama container victim")

    args = parser.parse_args()

    tracker = SystemTracker(
        session_id=args.session_id,
        duration=args.duration,
        interval=args.interval,
        output_dir=args.output_dir,
        container_aggressor=args.container_aggressor,
        container_victim=args.container_victim,
    )
    tracker.run()


if __name__ == "__main__":
    main()
