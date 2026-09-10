# SPDX-License-Identifier: MIT OR Apache-2.0
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guest"))
from dsq_experiment import check_other_tasks, choose_workers, task_state


class DsqExperimentTests(unittest.TestCase):
    def test_task_state_handles_spaces_and_parentheses_in_comm(self):
        self.assertEqual(task_state("123 (a name) with (parens)) T 1 2 3"), "T")

    def test_rejects_unrelated_ext_tasks_on_the_measured_cpu(self):
        files = [Path(f"/proc/{pid}/task/{pid}/stat") for pid in (100, 101, 102, 103)]
        with patch.object(Path, "glob", return_value=files), \
                patch("dsq_experiment.os.sched_getscheduler", return_value=7, create=True), \
                patch("dsq_experiment.os.sched_getaffinity", side_effect=[{0}, {1}, {0}], create=True), \
                patch.object(Path, "read_text", side_effect=["100 (hog) T 0", "103 (hog) R 0"]):
            with self.assertRaisesRegex(RuntimeError, r"\[103\]"):
                check_other_tasks(0, allowed={102})

    def test_selects_exact_counts_without_assuming_alternating_pids(self):
        processes = [Mock(pid=pid) for pid in (101, 103, 108, 110, 112)]
        with patch("dsq_experiment.stop_process") as stop:
            selected = choose_workers(3, 1, Mock(side_effect=processes))
        self.assertEqual([p.pid for p in selected], [101, 108, 110, 112])
        stop.assert_called_once_with(processes[1])

    def test_spawn_failure_cleans_up_previously_selected_workers(self):
        process = Mock(pid=100)
        with patch("dsq_experiment.stop_process") as stop:
            with self.assertRaises(OSError):
                choose_workers(1, 1, Mock(side_effect=[process, OSError("fork failed")]))
        stop.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
