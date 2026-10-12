"""Pembacaan statistik cgroups v2 dan status container Docker."""

import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


class CgroupReader:
    def __init__(self, container_name: str = "nn-aggressor"):
        self.container_name = container_name
        self.cgroup_dir: Optional[Path] = None

        # Latch pembacaan terakhir cgroups jika direktori dihapus saat container exit/OOM
        self.latched_stats = {
            "aggressor_cpu_usage_usec": 0,
            "aggressor_nr_throttled": 0,
            "aggressor_throttled_usec": 0,
            "aggressor_mem_current_mb": 0.0,
            "aggressor_oom_kill_count": 0,
            "aggressor_oom_killed": 0,
            "aggressor_oom_kill_second": None,
        }

    def discover_cgroup_dir(self) -> Optional[Path]:
        """Menemukan direktori cgroup v2 milik container (mendukung systemd cgroup driver)."""
        if not shutil.which("docker"):
            return None

        try:
            res = subprocess.run(
                ["docker", "inspect", "--format", "{{.Id}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode != 0 or not res.stdout.strip():
                return None
            full_id = res.stdout.strip()

            # 1. Jalur standar Docker dengan cgroup driver systemd (Ubuntu 22.04 LTS)
            systemd_path = Path(f"/sys/fs/cgroup/system.slice/docker-{full_id}.scope")
            if systemd_path.exists():
                return systemd_path

            # 2. Jalur alternatif cgroupfs
            cgroupfs_path = Path(f"/sys/fs/cgroup/docker/{full_id}")
            if cgroupfs_path.exists():
                return cgroupfs_path

            # 3. Pencarian dinamis jika path berbeda
            cgroup_root = Path("/sys/fs/cgroup")
            if cgroup_root.exists():
                for p in cgroup_root.glob(f"**/*{full_id}*"):
                    if p.is_dir():
                        return p
        except Exception as e:
            print(f"[Tracker/Cgroup] Gagal mencari cgroup untuk {self.container_name}: {e}", file=sys.stderr)

        return None

    @staticmethod
    def read_key_value_file(path: Path) -> Dict[str, int]:
        """Membaca berkas key-value cgroups v2 (seperti cpu.stat atau memory.events)."""
        stats = {}
        if not path.is_file():
            return stats
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            stats[parts[0]] = int(parts[1])
                        except ValueError:
                            pass
        except Exception:
            pass
        return stats

    def get_metrics(self, start_time: float) -> Dict:
        """Mengambil metrik cgroups v2 milik Aggressor Container."""
        if not self.cgroup_dir or not self.cgroup_dir.exists():
            self.cgroup_dir = self.discover_cgroup_dir()

        if self.cgroup_dir and self.cgroup_dir.exists():
            # 1. cpu.stat (nr_throttled, throttled_usec, usage_usec)
            cpu_stat = self.read_key_value_file(self.cgroup_dir / "cpu.stat")
            if cpu_stat:
                self.latched_stats["aggressor_cpu_usage_usec"] = cpu_stat.get("usage_usec", 0)
                self.latched_stats["aggressor_nr_throttled"] = cpu_stat.get("nr_throttled", 0)
                self.latched_stats["aggressor_throttled_usec"] = cpu_stat.get("throttled_usec", 0)

            # 2. memory.events (oom_kill)
            mem_events = self.read_key_value_file(self.cgroup_dir / "memory.events")
            if mem_events:
                oom_kills = mem_events.get("oom_kill", 0)
                self.latched_stats["aggressor_oom_kill_count"] = oom_kills
                if oom_kills > 0 and self.latched_stats["aggressor_oom_killed"] == 0:
                    self.latched_stats["aggressor_oom_killed"] = 1
                    self.latched_stats["aggressor_oom_kill_second"] = round(time.time() - start_time, 2)

            # 3. memory.current (penggunaan memori riil)
            mem_curr_file = self.cgroup_dir / "memory.current"
            if mem_curr_file.is_file():
                try:
                    val = int(mem_curr_file.read_text().strip())
                    self.latched_stats["aggressor_mem_current_mb"] = round(val / (1024 * 1024), 2)
                except Exception:
                    pass

        # Verifikasi docker inspect jika container berhenti atau terkena OOM
        self.verify_docker_oom(start_time)
        return dict(self.latched_stats)

    def verify_docker_oom(self, start_time: float):
        """Memeriksa status State.OOMKilled melalui docker inspect sebagai sumber kebenaran final."""
        if not shutil.which("docker"):
            return
        try:
            res = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.OOMKilled}}|{{.State.ExitCode}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                status, oom_killed, exit_code = res.stdout.strip().split("|")
                if oom_killed.lower() == "true":
                    if self.latched_stats["aggressor_oom_killed"] == 0:
                        self.latched_stats["aggressor_oom_kill_second"] = round(time.time() - start_time, 2)
                    self.latched_stats["aggressor_oom_killed"] = 1
                    if self.latched_stats["aggressor_oom_kill_count"] == 0:
                        self.latched_stats["aggressor_oom_kill_count"] = 1
        except Exception:
            pass
