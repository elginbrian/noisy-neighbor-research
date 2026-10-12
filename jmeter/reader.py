"""Pembaca dan pem-parsing berkas mentah .jtl (CSV/TSV) Apache JMeter."""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def read_jtl_samples(jtl_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    Membaca berkas .jtl dan mengelompokkan sampel ke dalam:
    (victim_samples, aggressor_samples).
    Setiap sampel dinormalisasi waktu relatifnya dalam detik (rel_time_s).
    """
    if not jtl_path.exists():
        raise FileNotFoundError(f"Berkas .jtl tidak ditemukan: {jtl_path}")

    victim_samples: List[Dict] = []
    aggressor_samples: List[Dict] = []
    min_timestamp: Optional[int] = None

    with open(jtl_path, "r", encoding="utf-8", errors="ignore") as f:
        header_line = f.readline()
        f.seek(0)
        delimiter = "\t" if "\t" in header_line else ","

        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                ts = int(row.get("timeStamp", 0))
                elapsed = float(row.get("elapsed", 0))
                label = row.get("label", "")
                rc = str(row.get("responseCode", "")).strip()
                success_str = str(row.get("success", "false")).lower()
                success = (success_str == "true") or (rc == "200")

                if min_timestamp is None or ts < min_timestamp:
                    min_timestamp = ts

                item = {
                    "timestamp": ts,
                    "elapsed_ms": elapsed,
                    "response_code": rc,
                    "success": success,
                }

                if "Victim" in label:
                    victim_samples.append(item)
                elif "Aggressor" in label:
                    aggressor_samples.append(item)
            except (ValueError, KeyError):
                continue

    base_ts = min_timestamp or 0
    for s in victim_samples:
        s["rel_time_s"] = round((s["timestamp"] - base_ts) / 1000.0, 2)
    for s in aggressor_samples:
        s["rel_time_s"] = round((s["timestamp"] - base_ts) / 1000.0, 2)

    return victim_samples, aggressor_samples
