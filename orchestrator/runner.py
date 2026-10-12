#!/usr/bin/env python3
"""
Skrip Utama Otomasi Pengujian (Orchestrator Runner) pada Tester Instance.
Sesuai Proposal Skripsi Bab 3.2.3, 3.3.4, 3.4.3, dan 3.4.4.

Mengoordinasikan:
- matrix.py         : Rencana 16 sel x 5 replikasi dalam urutan acak
- session_runner.py : Eksekusi siklus hidup per sesi
- ssh_client.py     : Akses remote ke Target Instance
- verifier.py       : Verifikasi batas cgroups v2
"""

import argparse
import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from dashboard import ExperimentState, start_dashboard_server
from matrix import EXPERIMENT_CELLS, generate_session_plan
from session_runner import SessionRunner
from ssh_client import SSHClient


def main():
    parser = argparse.ArgumentParser(description="Skrip Otomasi Pengujian (Tester Instance)")
    parser.add_argument("--target-ip", required=True, help="IP privat/publik Target Instance")
    parser.add_argument("--ssh-key", default="~/.ssh/noisy-neighbor", help="Path SSH private key")
    parser.add_argument("--ssh-user", default="ubuntu", help="User SSH remote")
    parser.add_argument("--output-dir", default="results", help="Direktori penyimpanan hasil")
    parser.add_argument("--mode", choices=["full", "pilot", "single"], default="pilot",
                        help="Mode eksekusi: full (80 sesi), pilot (16 sel x 1 rep), atau single (1 sel spesifik)")
    parser.add_argument("--cell", type=int, default=1, help="ID sel spesifik (1-16) jika mode single")
    parser.add_argument("--replications", type=int, default=None, help="Jumlah replikasi per sel (opsional override)")
    parser.add_argument("--idle-sec", type=int, default=30, help="Jeda idle antar sesi dalam detik (default: 30)")
    parser.add_argument("--seed", type=int, default=42, help="Seed acak untuk pengacakan urutan sesi")
    parser.add_argument("--dashboard-port", type=int, default=8080, help="Port web server dashboard (default: 8080)")
    parser.add_argument("--no-dashboard", action="store_true", help="Nonaktifkan web dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Cetak rencana sesi tanpa eksekusi")

    args = parser.parse_args()

    # 1. Tentukan parameter rencana sesi
    if args.mode == "single":
        cell_filter = [args.cell]
        reps = args.replications if args.replications else 1
    elif args.mode == "pilot":
        cell_filter = None
        reps = args.replications if args.replications else 1
    else:  # full
        cell_filter = None
        reps = args.replications if args.replications else 5

    sessions = generate_session_plan(
        replications=reps,
        shuffle=(args.mode != "single"),
        cell_filter=cell_filter,
        seed=args.seed,
    )

    print(f"=== [Orkestrator Pengujian] Mode: {args.mode.upper()} ===")
    print(f"Total sesi yang akan dieksekusi: {len(sessions)}")
    print(f"Target Instance IP              : {args.target_ip}")
    print(f"Jeda idle antar sesi           : {args.idle_sec}s\n")

    if args.dry_run:
        print("[Dry Run] Daftar urutan sesi:")
        for idx, s in enumerate(sessions, 1):
            print(f"  {idx:02d}. {s['session_id']} -> {s['cell_name']} (CPUs: {s['cpus']}, Mem: {s['memory']})")
        return

    root_dir = CURRENT_DIR.parent
    jmeter_dir = root_dir / "jmeter"
    output_dir = root_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2. Inisialisasi Web Dashboard Server
    state = ExperimentState(state_file=output_dir / "state.json", results_dir=output_dir)
    if not args.no_dashboard:
        start_dashboard_server(state, output_dir, port=args.dashboard_port)
        print(f"[Orkestrator] Dashboard Web Aktif: http://0.0.0.0:{args.dashboard_port}")
        print(f"              (Pantau progres dan unduh .zip hasil di browser Anda)\n")

    # 3. Inisialisasi Klien SSH dan Verifikasi Koneksi
    ssh = SSHClient(host=args.target_ip, user=args.ssh_user, key_path=args.ssh_key)
    print("[Orkestrator] Memeriksa konektivitas SSH ke Target Instance...")
    if not ssh.check_connection():
        print(f"[Orkestrator] ERROR: Tidak dapat terhubung ke {args.ssh_user}@{args.target_ip} via SSH!", file=sys.stderr)
        sys.exit(1)
    print("[Orkestrator] Koneksi SSH terverifikasi aktif.\n")

    # 4. Inisialisasi Session Runner
    runner = SessionRunner(
        ssh=ssh,
        target_ip=args.target_ip,
        jmeter_dir=jmeter_dir,
        state=state,
    )

    # 5. Loop Eksekusi Sesi
    state.start_experiment(args.mode.upper(), len(sessions))
    completed = 0
    failed = 0

    for idx, session in enumerate(sessions, 1):
        print(f"\n-------------------------------------------------------------")
        print(f"Mengeksekusi Sesi [{idx}/{len(sessions)}]: {session['session_id']} ({session['cell_name']})")
        print(f"-------------------------------------------------------------")

        state.set_current_session(session, "Mempersiapkan Target Instance...")
        result = runner.execute_session(session, output_dir)
        state.complete_session(result)

        if result is not None:
            completed += 1
        else:
            failed += 1

        # Jeda idle antar sesi sesuai Bab 3.4.4.C (kecuali pada sesi terakhir)
        if idx < len(sessions):
            msg = f"Jeda idle pemulihan host selama {args.idle_sec} detik..."
            print(f"\n[Orkestrator] {msg}")
            state.update_stage(msg, duration_sec=args.idle_sec)
            time.sleep(args.idle_sec)

    state.finish_experiment("COMPLETED" if failed == 0 else "PARTIAL")

    print(f"\n=============================================================")
    print(f"[Orkestrator Selesai] Total: {len(sessions)} | Sukses: {completed} | Gagal: {failed}")
    print(f"Seluruh log dan ringkasan tersimpan di direktori: {output_dir}")
    if not args.no_dashboard:
        print(f"Unduh seluruh hasil via web: http://<tester_ip>:{args.dashboard_port}/api/download/all")
        print(f"Dashboard web tetap aktif di port {args.dashboard_port}.")
        print(f"Tekan Ctrl+C untuk menghentikan server dashboard kapan saja.")
    print(f"=============================================================")

    if not args.no_dashboard:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Orkestrator] Server dashboard dihentikan. Selesai.")


if __name__ == "__main__":
    main()
