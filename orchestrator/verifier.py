"""Verifikasi penerapan limit cgroups v2 sebelum pengujian (Bab 3.4.4.D)."""

import sys
from typing import Dict, Tuple

from ssh_client import SSHClient


class CgroupVerifier:
    def __init__(self, ssh: SSHClient, container_name: str = "nn-aggressor"):
        self.ssh = ssh
        self.container_name = container_name

    def verify_limits(self, exp_cpu: str, exp_mem: str) -> Tuple[bool, Dict[str, str]]:
        """
        Membaca filesystem cgroups v2 milik container di Target Instance:
        - cpu.max
        - memory.max
        - io.max (harus kosong/tanpa limit, Bab 2.5.3)
        Mengembalikan (is_valid, actual_values).
        """
        # Script remote untuk mengambil isi cpu.max, memory.max, dan io.max
        remote_script = (
            f"CID=$(docker inspect --format '{{{{.Id}}}}' {self.container_name} 2>/dev/null) && "
            f"CGDIR=$(find /sys/fs/cgroup -maxdepth 3 -type d -name \"*$CID*\" 2>/dev/null | head -n 1) && "
            f"echo \"CPU:$(cat $CGDIR/cpu.max 2>/dev/null)\" && "
            f"echo \"MEM:$(cat $CGDIR/memory.max 2>/dev/null)\" && "
            f"echo \"IO:$(cat $CGDIR/io.max 2>/dev/null)\""
        )

        code, stdout, stderr = self.ssh.run(remote_script, timeout=10)
        if code != 0 or not stdout.strip():
            return False, {"error": f"Gagal membaca cgroups: {stderr}"}

        actual: Dict[str, str] = {}
        for line in stdout.strip().split("\n"):
            if line.startswith("CPU:"):
                actual["cpu"] = line[4:].strip()
            elif line.startswith("MEM:"):
                actual["mem"] = line[4:].strip()
            elif line.startswith("IO:"):
                actual["io"] = line[3:].strip()

        # 1. Validasi CPU
        cpu_val = actual.get("cpu", "").split()[0] if actual.get("cpu") else ""
        cpu_valid = (cpu_val == str(exp_cpu))

        # 2. Validasi Memori
        mem_val = actual.get("mem", "").strip()
        mem_valid = (mem_val == str(exp_mem))

        # 3. Validasi Disk I/O (harus kosong/tanpa limit blkio)
        io_val = actual.get("io", "").strip()
        io_valid = (io_val == "")

        is_valid = cpu_valid and mem_valid and io_valid
        if not is_valid:
            print(
                f"[Verifier] Validasi limit cgroups GAGAL untuk {self.container_name}:\n"
                f"  - CPU : terbaca '{actual.get('cpu')}', diharapkan '{exp_cpu}'\n"
                f"  - MEM : terbaca '{actual.get('mem')}', diharapkan '{exp_mem}'\n"
                f"  - IO  : terbaca '{actual.get('io')}', diharapkan kosong",
                file=sys.stderr,
            )

        return is_valid, actual
