"""Klien SSH dan SCP untuk eksekusi remote pada Target Instance."""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class SSHClient:
    def __init__(
        self,
        host: str,
        user: str = "ubuntu",
        key_path: str = "~/.ssh/noisy-neighbor",
    ):
        self.host = host
        self.user = user
        self.key_path = str(Path(key_path).expanduser())
        self.ssh_base = [
            "ssh",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            f"{self.user}@{self.host}",
        ]
        self.scp_base = [
            "scp",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
        ]

    def run(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Menjalankan perintah di host remote melalui SSH."""
        cmd = self.ssh_base + [command]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Perintah remote timeout ({timeout}s)"
        except Exception as e:
            return -1, "", str(e)

    def download_file(self, remote_path: str, local_path: Path, timeout: int = 30) -> bool:
        """Mengunduh berkas dari host remote ke lokal via SCP."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self.scp_base + [f"{self.user}@{self.host}:{remote_path}", str(local_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return res.returncode == 0
        except Exception:
            return False

    def check_connection(self) -> bool:
        """Memeriksa apakah koneksi SSH ke remote host dapat tersambung."""
        code, stdout, _ = self.run("echo pong", timeout=5)
        return code == 0 and "pong" in stdout
