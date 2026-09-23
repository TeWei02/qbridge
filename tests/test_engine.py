"""Tests for the Python engine, the circuit DSL and the CLI serialiser."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from qbridge import (  # noqa: E402
    StateVector,
    cli,  # noqa: E402
    engine,
    load_circuit,
    parse_circuit,
    run_circuit,
    run_text,
)

CIRCUITS = ROOT / "circuits"


def run_named(name: str) -> StateVector:
    return run_circuit(load_circuit(CIRCUITS / f"{name}.qc", name))


def test_single_qubit_identities():
    state = StateVector(1)
    assert state.probability(0) == 1.0
    state.apply_matrix(engine.single_qubit_matrix("h"), [0])
    assert state.probability(0) == pytest.approx(0.5, abs=1e-15)
    assert state.probability(1) == pytest.approx(0.5, abs=1e-15)
    state.apply_matrix(engine.single_qubit_matrix("h"), [0])
    assert state.probability(0) == pytest.approx(1.0, abs=1e-15)

    flipped = StateVector(2)
    flipped.apply_matrix(engine.single_qubit_matrix("x"), [1])
    assert flipped.probability(0b10) == pytest.approx(1.0, abs=1e-15)


def test_bell_pair():
    state = run_named("bell")
    assert state.probability(0) == pytest.approx(0.5, abs=1e-15)
    assert state.probability(3) == pytest.approx(0.5, abs=1e-15)
    assert state.probability(1) == pytest.approx(0.0, abs=1e-15)
    assert state.probability(2) == pytest.approx(0.0, abs=1e-15)


def test_ghz_state():
    state = run_named("ghz3")
    assert state.probability(0) == pytest.approx(0.5, abs=1e-15)
    assert state.probability(7) == pytest.approx(0.5, abs=1e-15)
    assert sum(state.probability(i) for i in range(1, 7)) == pytest.approx(0.0, abs=1e-15)


def test_deutsch_jozsa_balanced_has_no_zero_input_branch():
    state = run_named("deutsch_jozsa_balanced")
    zero_input_weight = sum(state.probability(i) for i in range(state.size()) if (i & 0b0111) == 0)
    assert zero_input_weight == pytest.approx(0.0, abs=1e-15)


def test_deutsch_jozsa_constant_keeps_zero_input_branch():
    state = run_named("deutsch_jozsa_constant")
    zero_input_weight = sum(state.probability(i) for i in range(state.size()) if (i & 0b0111) == 0)
    assert zero_input_weight == pytest.approx(1.0, abs=1e-15)


def test_grover_two_qubits_finds_marked_state():
    state = run_named("grover2")
    assert state.probability(0b11) == pytest.approx(1.0, abs=1e-15)


def test_qft_creates_uniform_superposition():
    state = run_named("qft3")
    for index in range(state.size()):
        assert state.probability(index) == pytest.approx(1.0 / state.size(), abs=1e-15)


@pytest.mark.parametrize(
    "name",
    [
        "bell",
        "ghz3",
        "deutsch_jozsa_balanced",
        "deutsch_jozsa_constant",
        "grover2",
        "qft3",
        "rotations3",
    ],
)
def test_every_circuit_preserves_norm(name):
    state = run_named(name)
    assert state.total_probability() == pytest.approx(1.0, abs=1e-12)


def test_rotation_gate_matches_pauli_up_to_phase():
    via_rz = StateVector(1)
    via_rz.apply_matrix(engine.single_qubit_matrix("h"), [0])
    via_rz.apply_matrix(engine.single_qubit_matrix("rz", engine.PI / 2), [0])
    via_s = StateVector(1)
    via_s.apply_matrix(engine.single_qubit_matrix("h"), [0])
    via_s.apply_matrix(engine.single_qubit_matrix("s"), [0])
    assert via_rz.probability(0) == pytest.approx(via_s.probability(0), abs=1e-15)
    assert abs(via_rz.amplitude(1)) == pytest.approx(abs(via_s.amplitude(1)), abs=1e-15)


def test_phase_gate_is_diagonal():
    state = StateVector(1)
    state.apply_matrix(engine.single_qubit_matrix("x"), [0])
    state.apply_matrix(engine.single_qubit_matrix("p", math.pi / 2), [0])
    assert state.amplitude(1) == pytest.approx(complex(0.0, 1.0), abs=1e-15)


def test_parse_angle_accepts_pi_multiples():
    from qbridge.circuit import parse_angle

    assert parse_angle("1.5") == 1.5
    assert parse_angle("pi") == pytest.approx(math.pi)
    assert parse_angle("pi/2") == pytest.approx(math.pi / 2)
    assert parse_angle("-pi/4") == pytest.approx(-math.pi / 4)


def test_dsl_reports_bad_input():
    with pytest.raises(ValueError):
        parse_circuit("h 0\n", "no-qubits")
    with pytest.raises(ValueError):
        parse_circuit("qubits 2\nfoo 0\n", "unknown-gate")
    with pytest.raises(ValueError):
        parse_circuit("qubits 2\ncx 0\n", "short-instruction")


def test_kernel_rejects_control_that_is_also_target():
    state = StateVector(2)
    with pytest.raises(ValueError):
        state.apply_matrix(engine.single_qubit_matrix("x"), [0], [0])


def test_kernel_rejects_out_of_range_qubit():
    state = StateVector(2)
    with pytest.raises(ValueError):
        state.apply_matrix(engine.single_qubit_matrix("x"), [5])


def test_three_qubit_controlled_gate_needs_both_controls():
    state = StateVector(3)
    state.apply_matrix(engine.single_qubit_matrix("x"), [2], [0, 1])
    assert state.probability(0) == pytest.approx(1.0, abs=1e-15)
    state.apply_matrix(engine.single_qubit_matrix("x"), [0])
    state.apply_matrix(engine.single_qubit_matrix("x"), [1])
    state.apply_matrix(engine.single_qubit_matrix("x"), [2], [0, 1])
    assert state.probability(0b111) == pytest.approx(1.0, abs=1e-15)


def test_run_text_shorthand():
    state = run_text("qubits 2\nh 0\ncx 0 1\n")
    assert state.probability(3) == pytest.approx(0.5, abs=1e-15)


def test_cli_json_shape():
    state = run_text("qubits 1\nh 0\n", "half")
    payload = cli.state_to_dict("half", state)
    assert payload["engine"] == "python"
    assert payload["qubits"] == 1
    assert payload["amplitudes"] == [[state.amplitude(0).real, 0.0], [state.amplitude(1).real, 0.0]]
    assert payload["support"][0]["index"] == 0
    assert len(payload["support"]) == 2


def test_cli_lists_and_runs_circuits(capsys):
    assert cli.main(["--list", "--dir", str(CIRCUITS)]) == 0
    listed = capsys.readouterr().out.split()
    assert "bell" in listed and "qft3" in listed

    assert cli.main(["--circuit", "bell", "--dir", str(CIRCUITS), "--json"]) == 0
    assert '"circuit": "bell"' in capsys.readouterr().out


def test_cli_rejects_unknown_circuit():
    with pytest.raises(FileNotFoundError):
        cli.resolve_circuit("does-not-exist", str(CIRCUITS))
