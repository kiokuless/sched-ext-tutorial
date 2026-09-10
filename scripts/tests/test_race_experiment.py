# SPDX-License-Identifier: MIT OR Apache-2.0
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guest"))
from race_experiment import Sample, phase_rates


class RaceExperimentTests(unittest.TestCase):
    def test_measures_two_to_one_and_b_accelerating_after_a_finishes(self):
        samples = []
        for t in range(1, 13):
            a = min(900, t * 100)
            b = t * 50 if t <= 9 else 450 + (t - 9) * 150
            samples.append(Sample(t, (a, b), (0.1, 0.1),
                                  (9 if t >= 9 else 0, 12 if t >= 12 else 0)))
        both, after_a = phase_rates(samples)
        self.assertEqual(both, (100, 50))
        self.assertEqual(after_a, (0, 150))

    def test_simultaneous_completion_does_not_invent_an_after_a_speed(self):
        samples = [Sample(t, (t * 100, t * 100), (0.1, 0.1),
                          (5, 5) if t == 5 else (0, 0)) for t in range(1, 6)]
        both, after_a = phase_rates(samples)
        self.assertEqual(both, (100, 100))
        self.assertIsNone(after_a)

    def test_short_phase_is_reported_as_unmeasurable(self):
        self.assertEqual(phase_rates([Sample(2, (10, 5), (0.1, 0.1), (0, 0))]),
                         (None, None))


if __name__ == "__main__":
    unittest.main()
