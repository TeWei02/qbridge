#!/usr/bin/env python3
"""Generate docs/reference.json from the Python engine.

The reference file is the single source of truth the C++, Python and JavaScript
engines are compared against, and it is also what the browser demo loads.
Every amplitude is produced here by simulating the `.qc` files in `circuits/`:
no number is typed in by hand, and nothing is presented as a hardware result.

If the C++ binary and the JavaScriptCore shell are available, the parity record
inside the JSON is filled in with the largest amplitude deviation each engine
shows against this reference. Missing engines are recorded as "not measured"
instead of being guessed.

Run from the repository root:

    python3 scripts/gen_reference.py
    python3 scripts/gen_reference.py --no-external   # Python only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "python"))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_parity  # noqa: E402
from qbridge import __version__, load_circuit, run_circuit  # noqa: E402

CIRCUITS_DIR = ROOT / "circuits"
OUTPUT = ROOT / "docs" / "reference.json"
TOLERANCE = 1e-12

META = {
    "bell": {
        "title": "Bell pair",
        "summary": "Hadamard on qubit 0 followed by CNOT. The two qubits are always read as equal, never as different.",
    },
    "ghz3": {
        "title": "Three-qubit GHZ state",
        "summary": "Greenberger-Horne-Zeilinger state: three qubits share one joint outcome.",
    },
    "deutsch_jozsa_balanced": {
        "title": "Deutsch-Jozsa, balanced oracle",
        "summary": "The oracle xors the parity of all three input qubits onto the ancilla.",
    },
    "deutsch_jozsa_constant": {
        "title": "Deutsch-Jozsa, constant oracle",
        "summary": "The oracle leaves the ancilla untouched, so the interference pattern is the opposite one.",
    },
    "grover2": {
        "title": "Grover search, two qubits",
        "summary": "One amplitude-amplification round with |11> marked as the target.",
    },
    "qft3": {
        "title": "Quantum Fourier transform, three qubits",
        "summary": "QFT applied to the basis state |001>, including the final bit-reversal swaps.",
    },
    "rotations3": {
        "title": "Rotation gates on three qubits",
        "summary": "rx, ry and rz on separate qubits, mixed with phases and entangling gates.",
    },
}


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise SystemExit(
            f"reference check failed for '{label}': the computed distribution does not match the documented behaviour"
        )


def support_of(probabilities: list[float]) -> list[dict]:
    return [
        {"index": index, "probability": probability}
        for index, probability in enumerate(probabilities)
        if probability > TOLERANCE
    ]


def zero_input_weight(probabilities: list[float], input_mask: int) -> float:
    """Total probability of the states where every input qubit reads 0."""
    return sum(
        probability for index, probability in enumerate(probabilities) if (index & input_mask) == 0
    )


def findings_for(name: str, probabilities: list[float]) -> list[str]:
    """Derive the readable conclusions of one circuit from its own amplitudes.

    Every statement below is checked against the computed distribution before it
    is written out, so the reference file cannot drift from the engine.
    """
    support = support_of(probabilities)
    findings: list[str] = []

    if name == "bell":
        _require(abs(probabilities[0] - 0.5) < TOLERANCE and abs(probabilities[3] - 0.5) < TOLERANCE, name)
        findings.append("Outcomes |00> and |11> carry probability 0.5 each; |01> and |10> never appear.")
        findings.append("Either qubit alone reads 0 or 1 with probability 0.5, so the correlation only shows up jointly.")
    elif name == "ghz3":
        _require(abs(probabilities[0] - 0.5) < TOLERANCE and abs(probabilities[7] - 0.5) < TOLERANCE, name)
        findings.append("Only |000> and |111> survive, 0.5 each; the other six basis states have probability 0.")
    elif name == "deutsch_jozsa_balanced":
        weight = zero_input_weight(probabilities, 0b0111)
        _require(weight < TOLERANCE, name)
        findings.append("Probability of reading 000 on the input register is 0, so the oracle is balanced.")
        findings.append("That is the single-query answer the algorithm is built to give.")
    elif name == "deutsch_jozsa_constant":
        weight = zero_input_weight(probabilities, 0b0111)
        _require(abs(weight - 1.0) < TOLERANCE, name)
        findings.append("Probability of reading 000 on the input register is 1, so the oracle is constant.")
        findings.append("The measured register matches the constant value, which is what the deterministic branch predicts.")
    elif name == "grover2":
        _require(abs(probabilities[3] - 1.0) < TOLERANCE, name)
        findings.append("One Grover iteration moves all probability onto the marked state |11>.")
        findings.append("With two qubits a single iteration is already exact, so the result is 1.0 rather than 0.95.")
    elif name == "qft3":
        uniform = 1.0 / len(probabilities)
        _require(all(abs(p - uniform) < TOLERANCE for p in probabilities), name)
        findings.append("All eight basis states carry probability 0.125.")
        findings.append("The input state was a computational basis state, so the QFT spreads it uniformly; the phase lives in the amplitudes.")
    elif name == "rotations3":
        findings.append(
            "Amplitude magnitudes: "
            + ", ".join(f"|{index:03b}> = {probabilities[index]:.3f}" for index in range(len(probabilities)))
        )
        findings.append("Mixing rotations with cz and ccx leaves a distribution that no single-qubit rotation could produce.")
    else:
        findings.append(f"{len(support)} basis states carry non-negligible probability.")

    _require(abs(sum(probabilities) - 1.0) < 1e-12, f"{name} normalisation")
    return findings


def collect() -> list[dict]:
    circuits = []
    for path in sorted(CIRCUITS_DIR.glob("*.qc")):
        circuit = load_circuit(path, path.stem)
        state = run_circuit(circuit)
        probabilities = state.probabilities()
        meta = META.get(path.stem, {})
        circuits.append(
            {
                "name": path.stem,
                "title": meta.get("title", path.stem),
                "summary": meta.get("summary", ""),
                "qubits": circuit.qubits,
                "gate_count": len(circuit.gates),
                "source": path.read_text(encoding="utf-8").strip(),
                "amplitudes": [[value.real, value.imag] for value in state.amplitudes],
                "probabilities": probabilities,
                "support": support_of(probabilities),
                "findings": findings_for(path.stem, probabilities),
            }
        )
    return circuits


def measure(entries: list[dict], results: dict) -> float:
    worst = 0.0
    for entry in entries:
        candidate = results[entry["name"]]
        worst = max(worst, check_parity.max_amplitude_delta(entry["amplitudes"], candidate["amplitudes"]))
        worst = max(worst, check_parity.max_probability_delta(entry["probabilities"], candidate["probabilities"]))
    return worst


def parity_record(entries: list[dict], arguments: argparse.Namespace) -> dict:
    record = {
        "python": {
            "status": "pass",
            "max_delta": 0.0,
            "note": "the reference file itself is produced by this engine",
        }
    }

    if arguments.no_external:
        for engine in ("cpp", "javascript"):
            record[engine] = {"status": "not measured", "note": "generated with --no-external"}
        return record

    binary = Path(arguments.cpp)
    try:
        cpp_results = check_parity.cpp_results(binary, entries)
    except SystemExit as failure:
        record["cpp"] = {"status": "not measured", "note": str(failure).split(";")[0]}
    except subprocess.CalledProcessError as failure:
        raise SystemExit(f"C++ parity run failed: {failure}") from failure
    else:
        worst = measure(entries, cpp_results)
        _require(worst <= TOLERANCE, f"C++ engine parity ({worst:.3e})")
        record["cpp"] = {"status": "pass", "max_delta": worst, "binary": str(binary)}

    try:
        jsc = check_parity.find_jsc(arguments.jsc)
        js = check_parity.js_results(jsc, entries)
    except SystemExit as failure:
        record["javascript"] = {"status": "not measured", "note": str(failure).split(";")[0]}
    else:
        worst = measure(entries, js)
        _require(worst <= TOLERANCE, f"JavaScript engine parity ({worst:.3e})")
        record["javascript"] = {"status": "pass", "max_delta": worst, "engine": str(jsc)}

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate docs/reference.json")
    parser.add_argument("--cpp", default=str(ROOT / "build" / "qbridge_cli"), help="C++ CLI binary")
    parser.add_argument("--jsc", default=None, help="path to the JavaScriptCore shell")
    parser.add_argument("--no-external", action="store_true", help="record only the Python engine")
    arguments = parser.parse_args()

    circuits = collect()
    payload = {
        "schema": 1,
        "generated_by": f"qbridge {__version__} (Python engine)",
        "generator_command": "python3 scripts/gen_reference.py",
        "tolerance": TOLERANCE,
        "note": (
            "Every amplitude in this file is the result of simulating the circuit on an ideal "
            "state vector with the Python engine of this repository. Nothing here was executed on "
            "quantum hardware and no number is hard coded."
        ),
        "parity": parity_record(circuits, arguments),
        "circuits": circuits,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} with {len(circuits)} circuits")
    for engine, entry in payload["parity"].items():
        if entry["status"] == "pass":
            print(f"  parity {engine:<11} max|delta| = {entry['max_delta']:.3e}")
        else:
            print(f"  parity {engine:<11} not measured ({entry['note']})")
    for entry in circuits:
        print(f"  {entry['name']:<26} qubits={entry['qubits']} gates={entry['gate_count']} support={len(entry['support'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
