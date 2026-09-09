# SPDX-License-Identifier: MIT OR Apache-2.0
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guest"))
from race_experiment import Sample
from team_race_experiment import phase_rates


class TeamRaceExperimentTests(unittest.TestCase):
    def samples(self, after_b):
        # Arrival begins at t=6. Newcomers start at t=7 and t=8; neither
        # the partially populated phase nor the startup burst belongs in rates.
        samples = [Sample(t, (100 * t, 100 * t, 0, 0), (0.1, 0.1, 0, 0), (0,) * 4)
                   for t in range(1, 6)]
        samples.extend([
            Sample(6, (999, 999, 0, 0), (0.1, 0.1, 0, 0), (0,) * 4),
            Sample(7, (999, 999, 999, 0), (0.1, 0.1, 7, 0), (0,) * 4),
            Sample(8, (999, 999, 999, 999), (0.1, 0.1, 7, 8), (0,) * 4),
        ])
        samples.extend(Sample(t, (1000 + 50 * (t - 8), 1000 + after_b * (t - 8),
                                  1000 + 50 * (t - 8), 1000 + 50 * (t - 8)),
                              (0.1, 0.1, 7, 8), (0,) * 4) for t in range(9, 13))
        return samples

    def test_detects_b_slowing_after_arrival(self):
        before, after = phase_rates(self.samples(after_b=50), arrival=6)
        self.assertEqual(before, (100, 100, 0, 0))
        self.assertEqual(after, (50, 50, 50, 50))
        self.assertEqual(after[1] / before[1], 0.5)

    def test_detects_b_preserving_its_speed(self):
        before, after = phase_rates(self.samples(after_b=100), arrival=6)
        self.assertEqual(after[1] / before[1], 1)

    def test_excludes_measurements_after_any_worker_finishes(self):
        samples = self.samples(after_b=50)
        samples.append(Sample(14, (2000,) * 4, (0.1, 0.1, 7, 8), (0, 0, 13, 0)))
        _, after = phase_rates(samples, arrival=6)
        self.assertEqual(after, (50, 50, 50, 50))

    def test_does_not_invent_after_rates_if_a_newcomer_never_runs(self):
        before, after = phase_rates(self.samples(after_b=50)[:7], arrival=6)
        self.assertIsNotNone(before)
        self.assertIsNone(after)

    def test_measures_seven_members_without_assuming_four_slots(self):
        samples = [Sample(t, (t * 100, t * 100) + (0,) * 6,
                          (0.1, 0.1) + (0,) * 6, (0,) * 8) for t in range(2, 6)]
        samples.extend(Sample(t, (t * 10, t * 100) + (t * 10,) * 6,
                              (0.1, 0.1) + (6,) * 6, (0,) * 8) for t in range(7, 11))
        before, after = phase_rates(samples, arrival=6)
        self.assertEqual(after[1] / before[1], 1)
        self.assertEqual(sum(after) - after[1], 70)


if __name__ == "__main__":
    unittest.main()
