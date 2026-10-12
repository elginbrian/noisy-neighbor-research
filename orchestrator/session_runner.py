"""Eksekutor siklus hidup satu sesi eksperimen (Bab 3.4.4 & Gambar 3.4.2)."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from ssh_client import SSHClient
from verifier import CgroupVerifier


class SessionRunner:
    def __init__(
        self,
        ssh: SSHClient,
        target_ip: str,
        jmeter_dir: Path,
        remote_project_dir: str = "/home/ubuntu",
        state: Optional[object] = None,
    ):
        self.ssh = ssh
        self.target_ip = target_ip
        self.jmeter_dir = jmeter_dir
        self.remote_project_dir = remote_project_dir
        self.state = state
        self.verifier = CgroupVerifier(ssh=ssh, container_name="nn-aggressor")

    def prepare_target(self, session: Dict, max_retries: int = 3) -> bool:
        """
        Mempersiapkan Target Instance:
        1. Hapus container lama (Bab 3.4.4.A)
        2. Bersihkan page cache kernel (Bab 3.4.4.B)
        3. Jalankan Victim & Aggressor dengan limit cgroups
        4. Verifikasi cgroups limit (Bab 3.4.4.D)
        """
        for attempt in range(1, max_retries + 1):
            print(f"[{session['session_id']}] Inisialisasi container di Target (Percobaan {attempt}/{max_retries})...")

            # 1. Reset container
            self.ssh.run("docker rm -f nn-aggressor nn-victim 2>/dev/null || true", timeout=15)

            # 2. Pembersihan page cache kernel
            self.ssh.run("sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null", timeout=10)

            # 3. Jalankan Victim Container (tanpa limit, restart=no)
            victim_cmd = "docker run -d --name nn-victim --restart=no -p 80:80 nn-victim:latest"
            code, _, err = self.ssh.run(victim_cmd, timeout=15)
            if code != 0:
                print(f"[{session['session_id']}] Gagal menjalankan Victim: {err}", file=sys.stderr)
                time.sleep(2)
                continue

            # 4. Jalankan Aggressor Container dengan batas cgroups
            limits = []
            if session.get("cpus"):
                limits.append(f"--cpus={session['cpus']}")
            if session.get("memory"):
                limits.append(f"--memory={session['memory']}")

            limit_str = " ".join(limits)
            aggressor_cmd = (
                f"docker run -d --name nn-aggressor --restart=no {limit_str} "
                f"-p 8000:8000 nn-aggressor:latest"
            )
            code, _, err = self.ssh.run(aggressor_cmd, timeout=15)
            if code != 0:
                print(f"[{session['session_id']}] Gagal menjalankan Aggressor: {err}", file=sys.stderr)
                time.sleep(2)
                continue

            # 5. Probe kesiapan HTTP /health
            if not self._wait_health(port=80) or not self._wait_health(port=8000):
                print(f"[{session['session_id']}] Probe /health gagal. Mengulangi inisialisasi...", file=sys.stderr)
                time.sleep(2)
                continue

            # 6. Verifikasi cgroups v2
            valid, _ = self.verifier.verify_limits(
                exp_cpu=session["exp_cpu"],
                exp_mem=session["exp_mem"],
            )
            if valid:
                print(f"[{session['session_id']}] Verifikasi limit cgroups SUKSES.")
                return True

            time.sleep(2)

        return False

    def _wait_health(self, port: int, timeout_sec: int = 15) -> bool:
        """Memeriksa kesiapan endpoint HTTP /health pada Target Instance."""
        probe_cmd = f"curl -s -f http://localhost:{port}/health >/dev/null"
        start = time.time()
        while time.time() - start < timeout_sec:
            code, _, _ = self.ssh.run(probe_cmd, timeout=3)
            if code == 0:
                return True
            time.sleep(1)
        return False

    def execute_session(self, session: Dict, output_dir: Path) -> Optional[Dict]:
        """Mengeksekusi satu sesi penuh: Persiapan -> Tracker -> JMeter -> Tarik Hasil."""
        sess_id = session["session_id"]
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Persiapan Target Instance
        if not self.prepare_target(session):
            print(f"[{sess_id}] ERROR: Gagal mempersiapkan Target Instance setelah percobaan ulang.", file=sys.stderr)
            return None

        # 2. Mulai Tracker di Target Instance (di latar belakang)
        if self.state:
            self.state.update_stage("Memulai Skrip Pemantau (Tracker) di Target Instance...")
        tracker_cmd = (
            f"nohup python3 {self.remote_project_dir}/monitoring/tracker.py "
            f"--session-id {sess_id} --duration 60 --interval 2 "
            f"--output-dir {self.remote_project_dir}/results "
            f">/dev/null 2>&1 &"
        )
        self.ssh.run(tracker_cmd, timeout=5)
        print(f"[{sess_id}] Tracker diaktifkan di Target Instance.")

        # 3. Jalankan JMeter di Tester Instance
        if self.state:
            self.state.update_stage("Menjalankan Injeksi Beban JMeter (10s baseline + 50s flood)...", duration_sec=60)
        jtl_path = output_dir / f"jmeter_{sess_id}.jtl"
        jmeter_sh = self.jmeter_dir / "run_test.sh"
        print(f"[{sess_id}] Memulai injeksi beban JMeter (durasi 60s)...")

        subprocess.run(
            [str(jmeter_sh), self.target_ip, sess_id, str(output_dir)],
            check=True,
        )

        # Beri jeda 2 detik memastikan tracker menulis data final
        time.sleep(2)

        # 4. Tarik berkas hasil dari Target Instance via SCP
        if self.state:
            self.state.update_stage("Menarik berkas log metrik via SCP...")
        remote_csv = f"{self.remote_project_dir}/results/metrics_{sess_id}.csv"
        remote_json = f"{self.remote_project_dir}/results/summary_{sess_id}.json"
        local_csv = output_dir / f"metrics_{sess_id}.csv"
        local_json = output_dir / f"summary_target_{sess_id}.json"

        self.ssh.download_file(remote_csv, local_csv)
        self.ssh.download_file(remote_json, local_json)
        print(f"[{sess_id}] Log metrik target berhasil ditarik ke lokal.")

        # 5. Gabungkan hasil ke combined JSON
        combined_file = output_dir / f"combined_{sess_id}.json"
        target_summary = {}
        if local_json.exists():
            with open(local_json, "r", encoding="utf-8") as f:
                target_summary = json.load(f)

        jmeter_summary = {}
        jmeter_json = output_dir / f"summary_jmeter_{sess_id}.json"
        if jmeter_json.exists():
            with open(jmeter_json, "r", encoding="utf-8") as f:
                jmeter_summary = json.load(f)

        combined = {
            "session_id": sess_id,
            "config": session,
            "target_metrics": target_summary,
            "jmeter_metrics": jmeter_summary,
        }
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)

        print(f"[{sess_id}] Sesi SELESAI. Ringkasan gabungan: {combined_file}")
        return combined
