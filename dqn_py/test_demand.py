"""Checks that paired demand is deterministic and includes all routes."""

import csv
import tempfile
import unittest
from pathlib import Path

from dqn_py.demand import generate_demand


class DemandTests(unittest.TestCase):
    def test_same_seed_same_requests_and_all_origins(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, c = (Path(tmp) / name for name in ("a.csv", "b.csv", "c.csv"))
            same_a = generate_demand(a, 5001, 400)
            same_b = generate_demand(b, 5001, 400)
            different = generate_demand(c, 5002, 400)
            self.assertEqual(same_a, same_b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertNotEqual(same_a, different)
            with a.open(newline="") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual({int(row[1]) for row in rows}, set(range(12)))
            self.assertEqual([int(row[0]) for row in rows],
                             sorted(int(row[0]) for row in rows))
            self.assertTrue(all(len(row) == 6 for row in rows))


if __name__ == "__main__":
    unittest.main()
