"""Small reference policies used by the controller comparison pipeline."""

import numpy as np


ACTION_ROWS = {
    0: (2, 6),  # NS through
    1: (3, 7),  # NS left
    2: (0, 4),  # EW through
    3: (1, 5),  # EW left
}


def pressure_heuristic(dtse, current_action=0, action_mask=None):
    """Choose a legal phase using queued speed delay in the DTSE."""
    occupancy, speed = dtse[0], dtse[1]
    weights = np.linspace(1.5, 0.5, 20)
    scores = np.zeros(4, dtype=np.float32)

    for action, rows in ACTION_ROWS.items():
        for row in rows:
            scores[action] += (occupancy[row] * (1.0 - speed[row] ** 2) * weights).sum()

    if action_mask is not None:
        scores[~np.asarray(action_mask, dtype=np.bool_)] = -np.inf
    if current_action in range(4) and (action_mask is None or action_mask[current_action]):
        scores[current_action] += 1.0  # discourage unnecessary phase changes

    return int(np.argmax(scores))
