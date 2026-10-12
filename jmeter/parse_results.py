#!/usr/bin/env python3
"""
Skrip Parser dan Agregator Hasil Apache JMeter (.jtl).
Sesuai Proposal Skripsi Tabel 3.3.1, Bab 3.4.4, dan Rumus (3.1).

Mengoordinasikan:
- reader.py    : Membaca berkas mentah .jtl
- calculator.py: Menghitung Victim Uptime, Latency P95, dan Waktu Tanggap Gangguan
- stats.py     : Utilitas statistik dasar
"""

import argparse
import json
import sys
from pathlib import Path

# Mendukung eksekusi langsung (python parse_results.py) maupun eksekusi modul
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from calculator import calculate_aggressor_metrics, calculate_victim_metrics
from reader import read_jtl_samples


def parse_jtl(
    jtl_path: Path,
    session_id: str,
    baseline_sec: float = 10.0,
    latency_threshold_ms: float = 1000.0,
) -> dict:
    """Membaca dan memproses berkas .jtl menjadi ringkasan metrik eksperimen."""
    victim_samples, aggressor_samples = read_jtl_samples(jtl_path)

    victim_metrics = calculate_victim_metrics(
        victim_samples=victim_samples,
        baseline_sec=baseline_sec,
        latency_threshold_ms=latency_threshold_ms,
    )
    aggressor_metrics = calculate_aggressor_metrics(aggressor_samples)

    return {
        "session_id": session_id,
        "victim_metrics": victim_metrics,
        "aggressor_metrics": aggressor_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Parser & Agregator Berkas .jtl Apache JMeter")
    parser.add_argument("--jtl", required=True, help="Path ke berkas .jtl hasil eksekusi JMeter")
    parser.add_argument("--session-id", default="session_jmeter", help="ID sesi pengujian")
    parser.add_argument("--baseline-sec", type=float, default=10.0, help="Durasi fase baseline detik (default: 10.0)")
    parser.add_argument("--threshold-ms", type=float, default=1000.0, help="Ambang batas latensi toleransi ms (default: 1000.0)")
    parser.add_argument("--output-json", default=None, help="Path berkas output JSON ringkasan")

    args = parser.parse_args()
    jtl_file = Path(args.jtl)

    summary = parse_jtl(
        jtl_path=jtl_file,
        session_id=args.session_id,
        baseline_sec=args.baseline_sec,
        latency_threshold_ms=args.threshold_ms,
    )

    out_file = Path(args.output_json) if args.output_json else jtl_file.with_name(f"jmeter_summary_{args.session_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[JMeter Parser] Berkas ringkasan berhasil disimpan ke: {out_file}")
    print(f"  - Victim Uptime: {summary['victim_metrics']['victim_uptime_pct']}%")
    print(f"  - Victim P95 Baseline Latency : {summary['victim_metrics']['baseline_latency_p95_ms']} ms")
    print(f"  - Victim P95 Injection Latency: {summary['victim_metrics']['injection_latency_p95_ms']} ms")
    if summary["victim_metrics"]["anomaly_response_latency_s"] is not None:
        print(f"  - Waktu Tanggap Gangguan (Rumus 3.1): {summary['victim_metrics']['anomaly_response_latency_s']} detik")
    else:
        print("  - Waktu Tanggap Gangguan: Tidak Terganggu (latensi selalu < 1000 ms)")


if __name__ == "__main__":
    main()
