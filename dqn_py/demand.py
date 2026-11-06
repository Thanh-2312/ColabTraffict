"""Controller-independent demand schedule for paired GAMA experiments."""

import csv
import hashlib
import random
from pathlib import Path


def generate_demand(path, seed, horizon):
    """Write the same requested arrivals for every controller at a given seed."""
    path = Path(path)
    rng = random.Random(seed)
    rows = []
    for origin in range(12):
        interval = 15 if origin < 2 else (45 if origin < 4 else 120)
        for cycle in range(0, horizon, interval):
            vtype = rng.choices([0, 1, 2], [.55, .38, .07])[0] if origin < 4 else 1
            speed = (25 + rng.randint(0, 12) if vtype == 0 else
                     30 + rng.randint(0, 15) if vtype == 1 else 22 + rng.randint(0, 10))
            turn = rng.choices([0, 1, 2, 3], [.60, .20, .15, .05])[0] if origin < 4 and vtype != 2 else 0
            lane = rng.randint(4, 11) if vtype == 0 else (8 if vtype == 2 else rng.choice([4, 8]))
            rows.append((cycle, origin, vtype, speed, turn, lane))
    rows.sort(key=lambda row: (row[0], row[1]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def demand_parameters(path):
    return [{"name": "demand_file_path", "type": "string", "value": str(Path(path).resolve())}]
