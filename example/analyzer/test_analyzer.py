#!/usr/bin/env python3
"""Tests for the analyzer: evaluate RPN and match against golden."""
import tempfile
import unittest
from pathlib import Path

ANALYZER_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = ANALYZER_DIR.parent
import sys
sys.path.insert(0, str(EXAMPLE_DIR))
sys.path.insert(0, str(ANALYZER_DIR))

import analyzer as analyzer_module


class TestAnalyzer(unittest.TestCase):
    """Test that analyzer evaluates RPN and compares to golden."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.orig_intermediate = analyzer_module.INTERMEDIATE_DIR
        analyzer_module.INTERMEDIATE_DIR = self.tmp

    def tearDown(self) -> None:
        analyzer_module.INTERMEDIATE_DIR = self.orig_intermediate

    def test_analyzer_reports_ok_when_computed_matches_golden(self) -> None:
        (self.tmp / "a.rpn").write_text("1 2 +")
        (self.tmp / "a.golden").write_text("3")
        result = analyzer_module.analyze()
        self.assertTrue(result.get("ready"))
        self.assertTrue(result.get("ok"))
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["results"][0]["ok"])
        self.assertEqual(result["results"][0]["computed"], 3)
        self.assertEqual(result["results"][0]["golden"], 3)

    def test_analyzer_reports_fail_when_computed_differs_from_golden(self) -> None:
        (self.tmp / "b.rpn").write_text("2 3 *")
        (self.tmp / "b.golden").write_text("5")  # wrong; 2*3=6
        result = analyzer_module.analyze()
        self.assertTrue(result.get("ready"))
        self.assertFalse(result.get("ok"))
        self.assertFalse(result["results"][0]["ok"])
        self.assertEqual(result["results"][0]["computed"], 6)
        self.assertEqual(result["results"][0]["golden"], 5)

    def test_analyzer_handles_missing_golden(self) -> None:
        (self.tmp / "c.rpn").write_text("1 2 +")
        # no c.golden
        result = analyzer_module.analyze()
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result["results"][0])


if __name__ == "__main__":
    unittest.main()
