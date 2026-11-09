import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from niptscale.jobs import run_commands


class RunCommandsTest(unittest.TestCase):
    def test_all_commands_are_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            command_file = Path(temp) / "commands.txt"
            command_file.write_text("echo one\necho two\n", encoding="utf-8")
            with patch("niptscale.jobs._run_one") as worker:
                worker.side_effect = lambda index, command: (index, 0)
                run_commands(command_file, parallel=2)
            self.assertEqual(worker.call_count, 2)

    def test_failure_is_propagated(self):
        with tempfile.TemporaryDirectory() as temp:
            command_file = Path(temp) / "commands.txt"
            command_file.write_text("false\n", encoding="utf-8")
            with patch("niptscale.jobs._run_one", return_value=(1, 7)):
                with self.assertRaises(RuntimeError):
                    run_commands(command_file, parallel=1)


if __name__ == "__main__":
    unittest.main()
