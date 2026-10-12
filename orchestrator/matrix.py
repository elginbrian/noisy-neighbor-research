"""Definisi Matriks Eksperimen 16 Sel dan Generator Rencana Pengujian."""

import random
from typing import Dict, List, Optional

# Matriks Penuh 16 Sel (Tabel 3.3.2 Proposal Skripsi)
# Total kapasitas Target Instance (t3.small) = 2 vCPU (200000 usec per 100000 usec period)
# - 75% kapasitas = 1.5 vCPU (150000 usec)
# - 50% kapasitas = 1.0 vCPU (100000 usec)
# - 25% kapasitas = 0.5 vCPU (50000 usec)
EXPERIMENT_CELLS: Dict[int, Dict] = {
    1:  {"name": "Sel 1 (Kontrol)",  "cpus": None,  "memory": None,   "exp_cpu": "max",    "exp_mem": "max"},
    2:  {"name": "Sel 2",            "cpus": None,  "memory": "768m", "exp_cpu": "max",    "exp_mem": 805306368},
    3:  {"name": "Sel 3",            "cpus": None,  "memory": "512m", "exp_cpu": "max",    "exp_mem": 536870912},
    4:  {"name": "Sel 4",            "cpus": None,  "memory": "256m", "exp_cpu": "max",    "exp_mem": 268435456},
    5:  {"name": "Sel 5",            "cpus": "1.5", "memory": None,   "exp_cpu": "150000", "exp_mem": "max"},
    6:  {"name": "Sel 6",            "cpus": "1.5", "memory": "768m", "exp_cpu": "150000", "exp_mem": 805306368},
    7:  {"name": "Sel 7",            "cpus": "1.5", "memory": "512m", "exp_cpu": "150000", "exp_mem": 536870912},
    8:  {"name": "Sel 8",            "cpus": "1.5", "memory": "256m", "exp_cpu": "150000", "exp_mem": 268435456},
    9:  {"name": "Sel 9",            "cpus": "1.0", "memory": None,   "exp_cpu": "100000", "exp_mem": "max"},
    10: {"name": "Sel 10",           "cpus": "1.0", "memory": "768m", "exp_cpu": "100000", "exp_mem": 805306368},
    11: {"name": "Sel 11",           "cpus": "1.0", "memory": "512m", "exp_cpu": "100000", "exp_mem": 536870912},
    12: {"name": "Sel 12",           "cpus": "1.0", "memory": "256m", "exp_cpu": "100000", "exp_mem": 268435456},
    13: {"name": "Sel 13",           "cpus": "0.5", "memory": None,   "exp_cpu": "50000",  "exp_mem": "max"},
    14: {"name": "Sel 14",           "cpus": "0.5", "memory": "768m", "exp_cpu": "50000",  "exp_mem": 805306368},
    15: {"name": "Sel 15",           "cpus": "0.5", "memory": "512m", "exp_cpu": "50000",  "exp_mem": 536870912},
    16: {"name": "Sel 16",           "cpus": "0.5", "memory": "256m", "exp_cpu": "50000",  "exp_mem": 268435456},
}


def generate_session_plan(
    replications: int = 5,
    shuffle: bool = True,
    cell_filter: Optional[List[int]] = None,
    seed: Optional[int] = 42,
) -> List[Dict]:
    """
    Menghasilkan rencana daftar sesi pengujian (default: 16 sel x 5 replikasi = 80 sesi).
    Urutan diacak (randomized order) sesuai Bab 3.3.4 & 3.4 guna mencegah bias residual.
    """
    target_cells = cell_filter if cell_filter else list(EXPERIMENT_CELLS.keys())
    sessions = []

    for cell_id in target_cells:
        cell_info = EXPERIMENT_CELLS[cell_id]
        for rep in range(1, replications + 1):
            session_id = f"cell_{cell_id:02d}_rep_{rep:02d}"
            sessions.append({
                "session_id": session_id,
                "cell_id": cell_id,
                "replication": rep,
                "cell_name": cell_info["name"],
                "cpus": cell_info["cpus"],
                "memory": cell_info["memory"],
                "exp_cpu": cell_info["exp_cpu"],
                "exp_mem": cell_info["exp_mem"],
            })

    if shuffle:
        if seed is not None:
            random.seed(seed)
        random.shuffle(sessions)

    return sessions
