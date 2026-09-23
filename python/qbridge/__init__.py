"""QBridge — a state-vector quantum circuit simulator with matching C++, Python
and JavaScript engines.

The three engines read the same `.qc` circuit files and produce amplitudes that
agree to within 1e-12, which is what the parity checks in `scripts/` verify.

Example:
    >>> from qbridge import load_text, run_text
    >>> state = run_text("qubits 2\nh 0\ncx 0 1\n")
    >>> round(state.probability(0), 3)
    0.5
    >>> round(state.probability(3), 3)
    0.5
"""

from __future__ import annotations

from . import circuit, engine
from .circuit import Circuit, GateSpec, load_circuit, load_circuit_dir, parse_circuit, run_circuit
from .engine import StateVector

__version__ = "1.0.0"

__all__ = [
    "Circuit",
    "GateSpec",
    "StateVector",
    "__version__",
    "circuit",
    "engine",
    "load_circuit",
    "load_circuit_dir",
    "parse_circuit",
    "run_circuit",
    "run_text",
]


def run_text(text: str, name: str = "circuit") -> StateVector:
    """Parse and run a circuit given as `.qc` text."""
    return run_circuit(parse_circuit(text, name))
