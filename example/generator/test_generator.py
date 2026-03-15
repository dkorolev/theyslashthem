#!/usr/bin/env python3
"""
Generator test: intermediate/ must exactly match what input/ implies.
Does NOT run the generator — it checks that current intermediate/ is correct.
Fails if: input changed and intermediates not regenerated, any input deleted and
intermediates not updated, anything added or changed in intermediate/.
"""
import unittest
from pathlib import Path

GENERATOR_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = GENERATOR_DIR.parent
import sys
sys.path.insert(0, str(EXAMPLE_DIR))
sys.path.insert(0, str(GENERATOR_DIR))

import expr

INPUT_DIR = EXAMPLE_DIR / "input"
INTERMEDIATE_DIR = EXAMPLE_DIR / "intermediate"


class TestGenerator(unittest.TestCase):
    """
    Assert that intermediate/ contents exactly match what input/ implies
    (expected .rpn and .golden per input file, computed via expr). No extras.
    """

    def test_intermediate_exactly_matches_input(self) -> None:
        txt_files = sorted(INPUT_DIR.glob("*.txt"))
        self.assertTrue(txt_files, "example/input/ must contain at least one .txt file")

        expected = {}
        for path in txt_files:
            stem = path.stem
            text = path.read_text().strip()
            expected[stem] = {
                "rpn": expr.expr_to_rpn_string(text),
                "golden": str(expr.expr_to_value(text)),
            }

        expected_stems = sorted(expected.keys())
        rpn_stems = sorted(p.stem for p in INTERMEDIATE_DIR.glob("*.rpn"))
        golden_stems = sorted(p.stem for p in INTERMEDIATE_DIR.glob("*.golden"))

        for stem in expected_stems:
            with self.subTest(input_file=f"{stem}.txt"):
                rpn_path = INTERMEDIATE_DIR / f"{stem}.rpn"
                golden_path = INTERMEDIATE_DIR / f"{stem}.golden"
                self.assertTrue(rpn_path.exists(), f"intermediate/{stem}.rpn missing")
                self.assertTrue(golden_path.exists(), f"intermediate/{stem}.golden missing")
                self.assertEqual(
                    rpn_path.read_text().strip(),
                    expected[stem]["rpn"],
                    f"intermediate/{stem}.rpn content does not match input/{stem}.txt",
                )
                self.assertEqual(
                    golden_path.read_text().strip(),
                    expected[stem]["golden"],
                    f"intermediate/{stem}.golden content does not match input/{stem}.txt",
                )

        self.assertEqual(
            rpn_stems,
            expected_stems,
            "intermediate/ has .rpn files that do not correspond to input files, "
            f"or is missing some; expected {expected_stems}, found {rpn_stems}",
        )
        self.assertEqual(
            golden_stems,
            expected_stems,
            "intermediate/ has .golden files that do not correspond to input files, "
            f"or is missing some; expected {expected_stems}, found {golden_stems}",
        )


if __name__ == "__main__":
    unittest.main()
