"""Pemulihan otomatis Target Instance yang hang (tidak responsif via SSH)."""

import sys
import time
from typing import Callable, Optional

from ssh_client import SSHClient


class TargetRecovery:
    def __init__(
        self,
        ssh: SSHClient,
        instance_id: Optional[str] = None,
        region: Optional[str] = None,
        log: Callable[[str], None] = print,
    ):
        self.ssh = ssh
        self.instance_id = instance_id
        self.region = region
        self.log = log

    def is_healthy(self, attempts: int = 2) -> bool:
        """Target sehat jika SSH merespons dan daemon Docker aktif."""
        for _ in range(attempts):
            code, out, _ = self.ssh.run("docker info >/dev/null 2>&1 && echo pong", timeout=20)
            if code == 0 and "pong" in out:
                return True
            time.sleep(3)
        return False

    def _reboot(self) -> bool:
        if not self.instance_id:
            return False
        try:
            import boto3  # noqa: WPS433

            ec2 = boto3.client("ec2", region_name=self.region)
            ec2.reboot_instances(InstanceIds=[self.instance_id])
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[Recovery] Gagal me-reboot Target via AWS API: {e}", file=sys.stderr)
            return False

    def _wait_healthy(self, timeout_sec: int) -> bool:
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.is_healthy(attempts=1):
                return True
            time.sleep(10)
        return False

    def recover(self, wait_sec: int = 600) -> bool:
        """Reboot Target (jika memungkinkan) lalu tunggu hingga sehat kembali."""
        self.log("[Recovery] Target Instance tidak responsif, memulai pemulihan otomatis...")

        # Beri kesempatan pulih sendiri sebelum reboot paksa
        if self._wait_healthy(60):
            self.log("[Recovery] Target pulih tanpa reboot.")
            return True

        if self._reboot():
            self.log("[Recovery] Perintah reboot Target terkirim, menunggu Target aktif kembali...")
            time.sleep(30)
        else:
            self.log("[Recovery] Reboot otomatis tidak tersedia, menunggu Target pulih sendiri...")

        if self._wait_healthy(wait_sec):
            self.log("[Recovery] Target Instance pulih dan siap digunakan.")
            return True

        self.log("[Recovery] Target Instance tidak pulih dalam batas waktu.")
        return False
