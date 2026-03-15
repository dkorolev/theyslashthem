#!/usr/bin/env python3
"""
Generator: reads .txt expressions from input/, produces for each in intermediate/:
1. Reverse Polish notation (.rpn)
2. Golden result of computation (.golden)
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = SCRIPT_DIR.parent
INPUT_DIR = EXAMPLE_DIR / "input"
INTERMEDIATE_DIR = EXAMPLE_DIR / "intermediate"

sys.path.insert(0, str(EXAMPLE_DIR))
from shared import expr


def generate() -> None:
    """For each .txt in input/, write .rpn and .golden into intermediate/ (overwriting)."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing .rpn and .golden so only current input set remains
    for p in list(INTERMEDIATE_DIR.glob("*.rpn")) + list(INTERMEDIATE_DIR.glob("*.golden")):
        p.unlink()

    txt_files = sorted(INPUT_DIR.glob("*.txt"))
    if not txt_files:
        raise SystemExit("No .txt files in input/")

    for path in txt_files:
        name = path.stem
        text = path.read_text().strip()
        rpn_str = expr.expr_to_rpn_string(text)
        value = expr.expr_to_value(text)
        (INTERMEDIATE_DIR / f"{name}.rpn").write_text(rpn_str)
        (INTERMEDIATE_DIR / f"{name}.golden").write_text(str(value))


if __name__ == "__main__":
    generate()
