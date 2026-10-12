"""Utilitas statistik dasar untuk agregasi metrik JMeter."""

from typing import List


def p95(values: List[float]) -> float:
    """Menghitung persentil ke-95 (P95)."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(0.95 * len(sorted_v))
    idx = min(idx, len(sorted_v) - 1)
    return round(sorted_v[idx], 2)


def mean(values: List[float]) -> float:
    """Menghitung nilai rata-rata aritmetika."""
    return round(sum(values) / len(values), 2) if values else 0.0
