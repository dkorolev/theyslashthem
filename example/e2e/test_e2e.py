#!/usr/bin/env python3
"""End-to-end: run generator (input → RPN + golden) then analyzer (evaluate RPN, match golden)."""
import json
import subprocess
import unittest
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
GENERATOR_DIR = EXAMPLE_DIR / "generator"
ANALYZER_DIR = EXAMPLE_DIR / "analyzer"


class TestE2E(unittest.TestCase):
    """Run generator then analyzer; all expressions must match golden."""

    def test_e2e_generator_then_analyzer(self) -> None:
        r1 = subprocess.run(
            ["python3", str(GENERATOR_DIR / "generator.py")],
            cwd=str(GENERATOR_DIR),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r1.returncode, 0, f"Generator failed: {r1.stderr}")

        r2 = subprocess.run(
            ["python3", str(ANALYZER_DIR / "analyzer.py")],
            cwd=str(ANALYZER_DIR),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r2.returncode, 0, f"Analyzer failed: {r2.stderr}")

        out = json.loads(r2.stdout)
        self.assertTrue(out.get("ready"))
        self.assertTrue(out.get("ok"), f"Analyzer reported failures: {out}")
        self.assertEqual(len(out["results"]), 9)  # 1.txt .. 9.txt
        for r in out["results"]:
            self.assertTrue(r["ok"], f"Case {r.get('name')}: {r}")


if __name__ == "__main__":
    unittest.main()
