"""Circuit DSL parser and executor (pure Python, mirrors the C++ header)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from . import engine

SINGLE_QUBIT_GATES = ("i", "id", "h", "x", "y", "z", "s", "sdg", "t", "tdg")
ROTATION_GATES = ("rx", "ry", "rz")


@dataclass
class GateSpec:
    """One gate instruction: which qubits it touches and its rotation angle."""

    name: str
    targets: list[int] = field(default_factory=list)
    controls: list[int] = field(default_factory=list)
    theta: float = 0.0


@dataclass
class Circuit:
    """A parsed circuit: a qubit count plus an ordered list of gates."""

    name: str
    qubits: int
    gates: list[GateSpec] = field(default_factory=list)


def strip_comment(line: str) -> str:
    """Drop `#` and `//` comments from a circuit line."""
    for marker in ("#", "//"):
        position = line.find(marker)
        if position != -1:
            line = line[:position]
    return line


def parse_angle(token: str) -> float:
    """Parse an angle written as a number or as a multiple of pi (`pi/2`, `-pi/4`)."""
    sign = -1.0 if token.startswith("-") else 1.0
    if "pi" in token:
        if "/" in token:
            return sign * math.pi / float(token.split("/", 1)[1])
        return sign * math.pi
    return float(token)


def parse_circuit(text: str, name: str = "circuit") -> Circuit:
    """Parse the shared `.qc` text format."""
    circuit = Circuit(name=name, qubits=0)
    for line_number, raw in enumerate(text.splitlines(), start=1):
        tokens = strip_comment(raw).split()
        if not tokens:
            continue

        def fail(reason: str, line_number: int = line_number) -> None:
            raise ValueError(f"circuit '{name}' line {line_number}: {reason}")

        if tokens[0] == "qubits":
            if len(tokens) != 2:
                fail("'qubits' takes exactly one argument")
            circuit.qubits = int(tokens[1])
            if not 1 <= circuit.qubits <= 30:
                fail("qubit count must be in [1, 30]")
            continue

        gate = GateSpec(name=tokens[0])
        if gate.name in ROTATION_GATES:
            if len(tokens) != 3:
                fail(f"{gate.name} expects: <theta> <target>")
            gate.theta = parse_angle(tokens[1])
            gate.targets = [int(tokens[2])]
        elif gate.name == "p":
            if len(tokens) != 3:
                fail("p expects: <theta> <target>")
            gate.theta = parse_angle(tokens[1])
            gate.targets = [int(tokens[2])]
        elif gate.name == "cp":
            if len(tokens) != 4:
                fail("cp expects: <theta> <control> <target>")
            gate.theta = parse_angle(tokens[1])
            gate.controls = [int(tokens[2])]
            gate.targets = [int(tokens[3])]
        elif gate.name in ("cx", "cz"):
            if len(tokens) != 3:
                fail(f"{gate.name} expects: <control> <target>")
            gate.controls = [int(tokens[1])]
            gate.targets = [int(tokens[2])]
        elif gate.name == "ccx":
            if len(tokens) != 4:
                fail("ccx expects: <control0> <control1> <target>")
            gate.controls = [int(tokens[1]), int(tokens[2])]
            gate.targets = [int(tokens[3])]
        elif gate.name == "swap":
            if len(tokens) != 3:
                fail("swap expects: <qubit0> <qubit1>")
            gate.targets = [int(tokens[1]), int(tokens[2])]
        elif gate.name in SINGLE_QUBIT_GATES:
            if len(tokens) != 2:
                fail(f"{gate.name} expects: <target>")
            gate.targets = [int(tokens[1])]
        else:
            fail(f"unknown gate '{gate.name}'")
        circuit.gates.append(gate)

    if circuit.qubits == 0:
        raise ValueError(f"circuit '{name}': missing 'qubits' line")
    return circuit


def load_circuit(path: str | Path, name: str | None = None) -> Circuit:
    """Read and parse a `.qc` file."""
    path = Path(path)
    return parse_circuit(path.read_text(encoding="utf-8"), name or path.stem)


def load_circuit_dir(directory: str | Path) -> list[Circuit]:
    """Parse every `.qc` file in `directory`, sorted by name."""
    directory = Path(directory)
    return [load_circuit(path) for path in sorted(directory.glob("*.qc"))]


def apply_gate(state: engine.StateVector, gate: GateSpec) -> None:
    """Apply one parsed gate to a state vector."""
    if gate.name == "cx":
        state.apply_matrix(engine.single_qubit_matrix("x"), gate.targets, gate.controls)
    elif gate.name == "cz":
        state.apply_matrix(engine.single_qubit_matrix("z"), gate.targets, gate.controls)
    elif gate.name == "cp":
        state.apply_matrix(engine.single_qubit_matrix("p", gate.theta), gate.targets, gate.controls)
    elif gate.name == "ccx":
        state.apply_matrix(engine.single_qubit_matrix("x"), gate.targets, gate.controls)
    elif gate.name == "swap":
        state.apply_matrix(engine.swap_matrix(), gate.targets)
    else:
        state.apply_matrix(
            engine.single_qubit_matrix(gate.name, gate.theta), gate.targets, gate.controls
        )


def run_circuit(circuit: Circuit) -> engine.StateVector:
    """Execute a parsed circuit and return the final state vector."""
    state = engine.StateVector(circuit.qubits)
    for gate in circuit.gates:
        apply_gate(state, gate)
    return state
