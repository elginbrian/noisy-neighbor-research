"""Kalkulasi metrik Victim Container dan Aggressor Container."""

from typing import Dict, List, Optional

from stats import mean, p95


def calculate_victim_metrics(
    victim_samples: List[Dict],
    baseline_sec: float = 10.0,
    latency_threshold_ms: float = 1000.0,
) -> Dict:
    """
    Menghitung metrik layanan Victim:
    - Victim Uptime (%) = (Jumlah Request Sukses / Total Request) * 100%
    - Victim Latency (P95) fase baseline (0-10s) dan fase injeksi (10-60s)
    - Waktu Tanggap Gangguan (Rumus 3.1)
    """
    total = len(victim_samples)
    success = sum(1 for s in victim_samples if s["success"])
    failed = total - success
    uptime_pct = round((success / total) * 100.0, 2) if total > 0 else 0.0

    baseline_lat = [s["elapsed_ms"] for s in victim_samples if s["rel_time_s"] < baseline_sec]
    injection_lat = [s["elapsed_ms"] for s in victim_samples if s["rel_time_s"] >= baseline_sec]

    base_p95 = p95(baseline_lat)
    inj_p95 = p95(injection_lat) if injection_lat else base_p95

    # Waktu Tanggap Gangguan (Rumus 3.1 Proposal):
    # Detik Mulai Layanan Melambat (>1000ms) - Detik Mulai Beban (10s)
    anomaly_response_latency_s: Optional[float] = None
    for s in victim_samples:
        if s["rel_time_s"] >= baseline_sec and s["elapsed_ms"] > latency_threshold_ms:
            anomaly_response_latency_s = round(s["rel_time_s"] - baseline_sec, 2)
            break

    return {
        "total_requests": total,
        "success_requests": success,
        "failed_requests": failed,
        "victim_uptime_pct": uptime_pct,
        "baseline_latency_p95_ms": base_p95,
        "baseline_latency_mean_ms": mean(baseline_lat),
        "injection_latency_p95_ms": inj_p95,
        "injection_latency_mean_ms": mean(injection_lat),
        "anomaly_response_latency_s": anomaly_response_latency_s,
        "service_degraded_over_1000ms": anomaly_response_latency_s is not None,
    }


def calculate_aggressor_metrics(aggressor_samples: List[Dict]) -> Dict:
    """Menghitung metrik beban HTTP flood Aggressor Container."""
    total = len(aggressor_samples)
    success = sum(1 for s in aggressor_samples if s["success"])
    failed = total - success
    latencies = [s["elapsed_ms"] for s in aggressor_samples]

    return {
        "total_flood_requests": total,
        "success_requests": success,
        "failed_requests": failed,
        "avg_latency_ms": mean(latencies),
        "p95_latency_ms": p95(latencies),
    }
