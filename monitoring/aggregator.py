"""Modul agregasi statistik sesuai Tabel 3.3.1 Proposal Skripsi."""

from typing import Dict, List


def p95(values: List[float]) -> float:
    """Menghitung persentil ke-95 (P95)."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(0.95 * len(sorted_v))
    idx = min(idx, len(sorted_v) - 1)
    return round(sorted_v[idx], 2)


def mean(values: List[float]) -> float:
    """Menghitung rata-rata aritmetika."""
    return round(sum(values) / len(values), 2) if values else 0.0


def calculate_aggregates(samples: List[Dict], session_id: str, latched_cgroup_stats: Dict) -> Dict:
    """
    Menghitung agregasi data sesuai metodologi Tabel 3.3.1:
    - Baseline Phase: detik 0 <= t < 10
    - Injection Phase: detik 10 <= t <= 60
    - Host CPU Utilization: Rata-rata fase injeksi (%)
    - Host Spare Memory: Nilai minimum fase injeksi (MB)
    - Host Disk I/O Throughput: Rata-rata fase injeksi (kB/s)
    - Host Disk I/O Latency: P95 fase injeksi (ms)
    - Aggressor CPU Throttling Frequency: Kumulatif
    - Aggressor OOM Kill Frequency: Kumulatif
    """
    if not samples:
        return {}

    baseline_samples = [s for s in samples if s["elapsed_s"] < 10.0]
    injection_samples = [s for s in samples if s["elapsed_s"] >= 10.0]

    # Evaluasi fase injeksi (atau seluruh sampel jika fase injeksi belum ada)
    target_eval = injection_samples if injection_samples else samples

    # Metrik Fase Injeksi
    cpu_inj = [s["host_cpu_pct"] for s in target_eval]
    spare_inj = [s["host_spare_mem_mb"] for s in target_eval]
    tp_inj = [s["host_disk_throughput_kbps"] for s in target_eval]
    await_inj = [s["host_disk_await_ms"] for s in target_eval]

    # Metrik Fase Baseline (detik 0-10) untuk komparasi Rumusan Masalah 1
    cpu_base = [s["host_cpu_pct"] for s in baseline_samples] if baseline_samples else cpu_inj
    spare_base = [s["host_spare_mem_mb"] for s in baseline_samples] if baseline_samples else spare_inj
    tp_base = [s["host_disk_throughput_kbps"] for s in baseline_samples] if baseline_samples else tp_inj
    await_base = [s["host_disk_await_ms"] for s in baseline_samples] if baseline_samples else await_inj

    last_sample = samples[-1]

    return {
        "session_id": session_id,
        "total_samples": len(samples),
        "actual_duration_s": round(last_sample["elapsed_s"], 2),
        "baseline": {
            "host_cpu_pct_mean": mean(cpu_base),
            "host_spare_mem_mb_min": min(spare_base) if spare_base else 0.0,
            "host_disk_throughput_kbps_mean": mean(tp_base),
            "host_disk_await_ms_p95": p95(await_base),
        },
        "injection": {
            "host_cpu_pct_mean": mean(cpu_inj),
            "host_spare_mem_mb_min": min(spare_inj) if spare_inj else 0.0,
            "host_disk_throughput_kbps_mean": mean(tp_inj),
            "host_disk_await_ms_p95": p95(await_inj),
        },
        "cgroup_interventions": {
            "aggressor_nr_throttled_cumulative": last_sample["aggressor_nr_throttled"],
            "aggressor_throttled_usec_cumulative": last_sample["aggressor_throttled_usec"],
            "aggressor_oom_kill_count": last_sample["aggressor_oom_kill_count"],
            "aggressor_oom_killed": last_sample["aggressor_oom_killed"],
            "aggressor_oom_kill_second": latched_cgroup_stats.get("aggressor_oom_kill_second"),
        },
    }
