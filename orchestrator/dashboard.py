"""Server Dashboard Web Progres dan Pengunduhan Hasil Eksperimen.

Menyediakan antarmuka web di port 8080 Tester Instance untuk:
1. Memantau progres eksekusi eksperimen secara real-time (auto-refresh).
2. Menampilkan tabel ringkasan metrik sesi yang telah selesai.
3. Mengunduh seluruh hasil pengujian dalam format berkas ZIP (.zip).
"""

import io
import json
import os
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional


class ExperimentState:
    """Menyimpan status eksekusi eksperimen yang dibaca oleh dashboard web."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "IDLE"  # IDLE, RUNNING, COMPLETED, FAILED
        self.mode = "PILOT"
        self.total_sessions = 0
        self.completed_count = 0
        self.failed_count = 0
        self.current_session: Optional[Dict] = None
        self.current_stage = "Menunggu inisiasi..."
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.history: List[Dict] = []

    def start_experiment(self, mode: str, total: int):
        with self.lock:
            self.status = "RUNNING"
            self.mode = mode
            self.total_sessions = total
            self.completed_count = 0
            self.failed_count = 0
            self.started_at = time.time()
            self.finished_at = None

    def set_current_session(self, session: Dict, stage: str):
        with self.lock:
            self.current_session = session
            self.current_stage = stage

    def update_stage(self, stage: str):
        with self.lock:
            self.current_stage = stage

    def complete_session(self, result: Optional[Dict]):
        with self.lock:
            if result:
                self.completed_count += 1
                self.history.append(result)
            else:
                self.failed_count += 1
            self.current_stage = "Sesi selesai."

    def finish_experiment(self, status: str = "COMPLETED"):
        with self.lock:
            self.status = status
            self.finished_at = time.time()
            self.current_stage = "Seluruh pengujian telah selesai."

    def load_existing_results(self, results_dir: Path):
        """Memuat riwayat sesi yang sudah ada di direktori results (untuk mode standalone)."""
        if not results_dir.exists():
            return
        combined_files = sorted(results_dir.glob("combined_*.json"))
        with self.lock:
            self.history = []
            for f in combined_files:
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        self.history.append(json.load(fp))
                except Exception:
                    pass
            self.completed_count = len(self.history)
            if self.completed_count > 0:
                self.total_sessions = self.completed_count
                self.status = "COMPLETED"
                self.current_stage = f"{self.completed_count} sesi hasil pengujian telah dimuat."

    def to_dict(self) -> Dict:
        with self.lock:
            elapsed = 0
            if self.started_at:
                end = self.finished_at or time.time()
                elapsed = round(end - self.started_at, 1)

            pct = 0.0
            if self.total_sessions > 0:
                pct = round((self.completed_count / self.total_sessions) * 100.0, 1)

            return {
                "status": self.status,
                "mode": self.mode,
                "total_sessions": self.total_sessions,
                "completed_count": self.completed_count,
                "failed_count": self.failed_count,
                "progress_pct": pct,
                "elapsed_sec": elapsed,
                "current_stage": self.current_stage,
                "current_session": self.current_session,
                "history": self.history,
            }


TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"


def get_html_content() -> bytes:
    """Membaca berkas template HTML dari folder templates/index.html."""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_bytes()
    return b"<!DOCTYPE html><html><body><h1>Template templates/index.html tidak ditemukan!</h1></body></html>"


class DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, state: ExperimentState, results_dir: Path, *args, **kwargs):
        self.state = state
        self.results_dir = results_dir
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html_bytes = get_html_content()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)

        elif self.path == "/api/progress":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps(self.state.to_dict())
            self.wfile.write(data.encode("utf-8"))

        elif self.path == "/api/download/all":
            self._handle_download_zip()

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def _handle_download_zip(self):
        """Mengemas seluruh berkas di folder results ke dalam berkas ZIP."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            if self.results_dir.exists():
                for p in self.results_dir.rglob("*"):
                    if p.is_file():
                        arcname = p.relative_to(self.results_dir)
                        try:
                            zf.write(p, arcname)
                            file_count += 1
                        except Exception:
                            pass
            if file_count == 0:
                zf.writestr(
                    "README.txt",
                    "Belum ada berkas hasil pengujian yang tersimpan di folder results.\n"
                )

        buf.seek(0)
        zip_bytes = buf.getvalue()

        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", 'attachment; filename="noisy_neighbor_results.zip"')
        self.send_header("Content-Length", str(len(zip_bytes)))
        self.end_headers()
        self.wfile.write(zip_bytes)

    def log_message(self, format, *args):
        # Meredam logging akses HTTP bawaan agar tidak mengotori terminal orkestrator
        pass


def make_handler(state: ExperimentState, results_dir: Path):
    return lambda *args, **kwargs: DashboardHandler(state, results_dir, *args, **kwargs)


def start_dashboard_server(state: ExperimentState, results_dir: Path, port: int = 8080) -> HTTPServer:
    """Menjalankan server dashboard di latar belakang (daemon thread)."""
    server = HTTPServer(("0.0.0.0", port), make_handler(state, results_dir))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Server Dashboard Web Pemantauan Eksperimen")
    parser.add_argument("--port", type=int, default=8080, help="Port web server (default: 8080)")
    parser.add_argument("--results-dir", default="results", help="Path direktori penyimpanan hasil (default: results)")
    args = parser.parse_args()

    res_dir = Path(args.results_dir).resolve()
    res_dir.mkdir(parents=True, exist_ok=True)

    state = ExperimentState()
    state.load_existing_results(res_dir)

    print("=============================================================")
    print("  Dashboard Web Noisy Neighbor Research (Standalone)")
    print("=============================================================")
    print(f"Server aktif di        : http://0.0.0.0:{args.port}")
    print(f"Direktori hasil        : {res_dir}")
    print(f"Sesi riwayat terdeteksi: {state.completed_count}")
    print("Tekan Ctrl+C untuk menghentikan server.")
    print("=============================================================\n")

    httpd = HTTPServer(("0.0.0.0", args.port), make_handler(state, res_dir))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dashboard] Server dihentikan oleh pengguna.")

