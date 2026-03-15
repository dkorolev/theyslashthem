# Example: generator → analyze

This example illustrates the workflow from the main README: one part **generates** intermediate outputs and another **analyzes** them. Layout is split by **directory boundary** for slicing: **generator/** and **analyzer/** are self-contained slices (code + their tests); **e2e/** holds the end-to-end test.

## Layout

- **`input/`** — Input text files `1.txt` … `9.txt`, each containing a math expression (digits, +, -, *, /, parentheses).
- **`generator/`** — Generator slice: code and tests. For each `.txt` in `input/`, writes into **`intermediate/`** the `.rpn` and `.golden` files.
- **`intermediate/`** — Populated by the generator: one `.rpn` and one `.golden` per input file.
- **`analyzer/`** — Analyzer slice: code and tests. Reads each `intermediate/*.rpn`, evaluates it and checks against `intermediate/*.golden`.
- **`e2e/`** — End-to-end test: runs generator then analyzer and asserts all pass.
- **`expr.py`** — Shared expression/RPN logic (used by both generator and analyzer).

## Scripts

- **`generator/run.sh`** — Run the generator.
- **`generator/run_test_generator.sh`** — Run generator tests (used by CI).
- **`analyzer/run.sh`** — Run the analyzer.
- **`analyzer/run_test_analyzer.sh`** — Run analyzer tests (used by CI).
- **`e2e/run_test_e2e.sh`** — Run e2e test (used by CI).
- **`run_e2e.sh`** — Run generator then analyzer (end-to-end pipeline).

## GitHub workflows

Three workflows, each runs one script:

- **generator** — `./example/generator/run_test_generator.sh`
- **analyzer** — `./example/analyzer/run_test_analyzer.sh`
- **e2e** — `./example/e2e/run_test_e2e.sh`

## Flow

1. Generator reads each `input/*.txt`, computes RPN and the result, writes `intermediate/〈name〉.rpn` and `intermediate/〈name〉.golden`.
2. Analyzer reads each `intermediate/*.rpn`, evaluates the RPN, and compares the value to `intermediate/*.golden`.
