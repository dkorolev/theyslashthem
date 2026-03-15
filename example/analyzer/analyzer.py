#!/usr/bin/env python3
"""
Analyzer: reads .rpn and .golden from the intermediate directory (written by the generator).
Evaluates each RPN and checks the result against the golden value.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = SCRIPT_DIR.parent
INTERMEDIATE_DIR = EXAMPLE_DIR / "intermediate"

sys.path.insert(0, str(EXAMPLE_DIR))
import expr


def analyze() -> dict:
    """
    For each .rpn in intermediate/, evaluate it and compare to the matching .golden.
    Returns a result dict with ok, failed list, and details.
    """
    rpn_files = sorted(INTERMEDIATE_DIR.glob("*.rpn"))
    results = []
    all_ok = True

    for rpn_path in rpn_files:
        name = rpn_path.stem
        golden_path = INTERMEDIATE_DIR / f"{name}.golden"
        if not golden_path.exists():
            results.append({"name": name, "ok": False, "error": "missing .golden"})
            all_ok = False
            continue
        try:
            rpn_str = rpn_path.read_text().strip()
            golden_val = int(golden_path.read_text().strip())
            computed = expr.evaluate_rpn(expr.rpn_from_string(rpn_str))
            ok = computed == golden_val
            if not ok:
                all_ok = False
            results.append({
                "name": name,
                "ok": ok,
                "computed": computed,
                "golden": golden_val,
            })
        except Exception as e:
            results.append({"name": name, "ok": False, "error": str(e)})
            all_ok = False

    return {"ready": True, "ok": all_ok, "results": results}


def main() -> None:
    result = analyze()
    import json
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        exit(1)


if __name__ == "__main__":
    main()
