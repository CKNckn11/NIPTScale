import tempfile
import unittest
from pathlib import Path

from niptscale.config import Settings
from niptscale.scanner import discover, write_manifests


class ScannerTest(unittest.TestCase):
    def test_discover_and_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lane = root / "Disk10" / "V1" / "L02"
            lane.mkdir(parents=True)
            (lane / "V1_L02_1.fq.gz").write_bytes(b"x" * 20)
            (lane / "undecoded.fq.gz").write_bytes(b"x" * 20)
            settings = Settings(root, root / "results", root / "pipeline", min_fastq_bytes=10)
            lanes, fastqs = discover(settings)
            self.assertEqual(len(lanes), 1)
            self.assertEqual(lanes[0].included_fastq, 1)
            self.assertEqual(lanes[0].excluded_fastq, 1)
            paths = write_manifests(root / "manifest", lanes, fastqs)
            self.assertIn(str(lane.resolve()), paths["lanes"].read_text())

    def test_parallel_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = Settings(root, root, root)
            self.assertEqual(settings.alignment_lane_jobs, 4)
            self.assertEqual(settings.samples_per_lane, 2)
            self.assertEqual(settings.alignment_threads_per_sample, 4)


if __name__ == "__main__":
    unittest.main()
