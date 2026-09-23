#!/usr/bin/env python3
"""Cross-engine parity check.

Feeds the same `.qc` circuits to all three engines and compares the resulting
amplitudes against docs/reference.json:

  * Python  — the pure-Python package in `python/qbridge`
  * C++     — the `qbridge_cli` binary built by CMake (`build/qbridge_cli`)
  * JS      — `docs/qbridge.js` executed by the JavaScriptCore shell (`jsc`)

Usage (from the repository root):

    python3 scripts/check_parity.py
    python3 scripts/check_parity.py --cpp build/qbridge_cli --jsc "$(command -v jsc)"

Exits non-zero as soon as one engine is missing or one amplitude drifts beyond
the tolerance stored in the reference file.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from qbridge import load_circuit, run_circuit  # noqa: E402

REFERENCE = ROOT / "docs" / "reference.json"
JS_ENGINE = ROOT / "docs" / "qbridge.js"
CIRCUITS_DIR = ROOT / "circuits"

DEFAULT_JSC_CANDIDATES = [
    "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc",
]


def load_reference() -> dict:
    if not REFERENCE.is_file():
        raise SystemExit("docs/reference.json is missing; run python3 scripts/gen_reference.py first")
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def python_results(entries: list[dict]) -> dict:
    results = {}
    for entry in entries:
        circuit = load_circuit(CIRCUITS_DIR / f"{entry['name']}.qc", entry["name"])
        state = run_circuit(circuit)
        results[entry["name"]] = {
            "amplitudes": [[value.real, value.imag] for value in state.amplitudes],
            "probabilities": state.probabilities(),
        }
    return results


def cpp_results(binary: Path, entries: list[dict]) -> dict:
    if not binary.is_file():
        raise SystemExit(f"C++ binary not found at {binary}; build it with: cmake -B build && cmake --build build")
    results = {}
    for entry in entries:
        completed = subprocess.run(
            [str(binary), "--circuit", entry["name"], "--dir", str(CIRCUITS_DIR), "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        results[entry["name"]] = {
            "amplitudes": payload["amplitudes"],
            "probabilities": payload["probabilities"],
        }
    return results


def find_jsc(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
        raise SystemExit(f"jsc not found at {explicit}")
    for candidate in DEFAULT_JSC_CANDIDATES:
        if Path(candidate).is_file():
            return Path(candidate)
    found = shutil.which("jsc")
    if found:
        return Path(found)
    raise SystemExit(
        "JavaScriptCore shell not found; pass --jsc <path>. "
        "The JavaScript engine cannot be verified without it."
    )


def js_results(jsc: Path, entries: list[dict]) -> dict:
    if not JS_ENGINE.is_file():
        raise SystemExit(f"missing {JS_ENGINE}")
    driver = f"""
load({json.dumps(str(JS_ENGINE))});
var circuits = {json.dumps([{"name": e["name"], "source": e["source"]} for e in entries])};
var out = {{}};
circuits.forEach(function (entry) {{
  out[entry.name] = QBridge.stateToDict(QBridge.runText(entry.source, entry.name), entry.name, "javascript");
}});
print(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as directory:
        script = Path(directory) / "parity_driver.js"
        script.write_text(driver, encoding="utf-8")
        completed = subprocess.run([str(jsc), str(script)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"jsc failed: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    return {
        name: {"amplitudes": value["amplitudes"], "probabilities": value["probabilities"]}
        for name, value in payload.items()
    }


def max_amplitude_delta(left: list, right: list) -> float:
    worst = 0.0
    for left_row, right_row in zip(left, right, strict=False):
        for a, b in zip(left_row, right_row, strict=False):
            worst = max(worst, abs(a - b))
    return worst


def max_probability_delta(left: list, right: list) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=False))


def compare(label: str, reference: dict, candidate: dict, tolerance: float) -> tuple[bool, float]:
    ok = True
    worst = 0.0
    for entry in reference["circuits"]:
        name = entry["name"]
        if name not in candidate:
            print(f"  MISSING {label}: {name}")
            ok = False
            continue
        amplitude_delta = max_amplitude_delta(entry["amplitudes"], candidate[name]["amplitudes"])
        probability_delta = max_probability_delta(entry["probabilities"], candidate[name]["probabilities"])
        delta = max(amplitude_delta, probability_delta)
        worst = max(worst, delta)
        status = "ok" if delta <= tolerance else "FAIL"
        if delta > tolerance:
            ok = False
        print(f"  {label:<8} {name:<26} max|delta| = {delta:.3e}  {status}")
    return ok, worst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp", default=str(ROOT / "build" / "qbridge_cli"), help="path to the C++ CLI binary")
    parser.add_argument("--jsc", default=None, help="path to the JavaScriptCore shell")
    parser.add_argument("--python-only", action="store_true", help="only regenerate the Python results")
    parser.add_argument(
        "--allow-missing-js",
        action="store_true",
        help="report a missing JavaScriptCore shell as skipped instead of failing (used by CI images without jsc)",
    )
    arguments = parser.parse_args()

    reference = load_reference()
    tolerance = reference["tolerance"]
    entries = reference["circuits"]
    print(f"reference: {REFERENCE.relative_to(ROOT)}  ({len(entries)} circuits, tolerance {tolerance:g})")

    print("\npython vs reference")
    python_ok, python_worst = compare("python", reference, python_results(entries), tolerance)

    if arguments.python_only:
        print(f"\nworst python delta: {python_worst:.3e}")
        return 0 if python_ok else 1

    print("\ncpp vs reference")
    cpp_ok, cpp_worst = compare("cpp", reference, cpp_results(Path(arguments.cpp), entries), tolerance)

    print("\njavascript vs reference")
    js_ok = True
    js_worst = 0.0
    try:
        engine = find_jsc(arguments.jsc)
    except SystemExit as failure:
        if not arguments.allow_missing_js:
            raise
        print(f"  skipped: {failure}")
    else:
        js_ok, js_worst = compare("js", reference, js_results(engine, entries), tolerance)

    print("\nsummary")
    print(f"  python worst delta:     {python_worst:.3e}")
    print(f"  cpp worst delta:        {cpp_worst:.3e}")
    print(f"  javascript worst delta: {js_worst:.3e}" + ("" if js_ok else "  (FAILED)"))
    passed = python_ok and cpp_ok and js_ok
    print(f"  result: {'PASS' if passed else 'FAIL'} (tolerance {tolerance:g})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
