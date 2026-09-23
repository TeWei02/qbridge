"""State-vector simulator core (pure Python).

The kernel mirrors ``include/qbridge/statevector.hpp`` operation for operation:
gates are dense matrices applied to the amplitudes selected by their target
qubits, in the same summation order. That is what lets the C++, Python and
JavaScript engines agree to floating-point rounding.

This module deliberately avoids NumPy: the repository's parity contract is
"same operations, same order", and a plain list of complex numbers keeps that
contract readable and dependency free.
"""

from __future__ import annotations

import math

PI = 3.14159265358979323846
INV_SQRT2 = 0.70710678118654752440

Matrix = list  # list[list[complex]]


def identity_matrix(dimension: int) -> Matrix:
    """Return the `dimension` x `dimension` identity matrix."""
    return [
        [complex(1.0, 0.0) if row == column else complex(0.0, 0.0) for column in range(dimension)]
        for row in range(dimension)
    ]


def from_polar(radius: float, angle: float) -> complex:
    """Complex number of the given radius and angle, written as cos + i sin."""
    return complex(radius * math.cos(angle), radius * math.sin(angle))


def single_qubit_matrix(name: str, theta: float = 0.0) -> Matrix:
    """2x2 matrix for a single-qubit gate; `theta` is used by rotations."""
    one = complex(1.0, 0.0)
    zero = complex(0.0, 0.0)
    i = complex(0.0, 1.0)

    if name in ("i", "id"):
        return [[one, zero], [zero, one]]
    if name == "h":
        a = complex(INV_SQRT2, 0.0)
        b = complex(-INV_SQRT2, 0.0)
        return [[a, a], [a, b]]
    if name == "x":
        return [[zero, one], [one, zero]]
    if name == "y":
        return [[zero, -i], [i, zero]]
    if name == "z":
        return [[one, zero], [zero, -one]]
    if name == "s":
        return [[one, zero], [zero, i]]
    if name == "sdg":
        return [[one, zero], [zero, -i]]
    if name == "t":
        return [[one, zero], [zero, from_polar(1.0, PI / 4.0)]]
    if name == "tdg":
        return [[one, zero], [zero, from_polar(1.0, -PI / 4.0)]]
    if name in ("p", "u1"):
        return [[one, zero], [zero, from_polar(1.0, theta)]]

    if name in ("rx", "ry", "rz"):
        cosine = math.cos(theta / 2.0)
        sine = math.sin(theta / 2.0)
        if name == "rx":
            return [
                [complex(cosine, 0.0), complex(0.0, -sine)],
                [complex(0.0, -sine), complex(cosine, 0.0)],
            ]
        if name == "ry":
            return [
                [complex(cosine, 0.0), complex(-sine, 0.0)],
                [complex(sine, 0.0), complex(cosine, 0.0)],
            ]
        return [
            [complex(math.cos(-theta / 2.0), math.sin(-theta / 2.0)), zero],
            [zero, complex(math.cos(theta / 2.0), math.sin(theta / 2.0))],
        ]

    raise ValueError(f"unknown single-qubit gate: {name}")


def swap_matrix() -> Matrix:
    """4x4 matrix that exchanges the amplitudes of two qubits."""
    matrix = identity_matrix(4)
    matrix[1][1] = complex(0.0, 0.0)
    matrix[2][2] = complex(0.0, 0.0)
    matrix[1][2] = complex(1.0, 0.0)
    matrix[2][1] = complex(1.0, 0.0)
    return matrix


class StateVector:
    """Dense state vector initialised to |0...0>."""

    MAX_QUBITS = 24  # memory bound for the pure-Python engine

    def __init__(self, qubits: int) -> None:
        if qubits < 1 or qubits > self.MAX_QUBITS:
            raise ValueError(f"qubit count must be in [1, {self.MAX_QUBITS}]")
        self.qubits = qubits
        self.amplitudes = [complex(0.0, 0.0)] * (1 << qubits)
        self.amplitudes[0] = complex(1.0, 0.0)

    def num_qubits(self) -> int:
        return self.qubits

    def size(self) -> int:
        return len(self.amplitudes)

    def amplitude(self, index: int) -> complex:
        return self.amplitudes[index]

    def probability(self, index: int) -> float:
        return abs(self.amplitudes[index]) ** 2

    def probabilities(self) -> list[float]:
        return [abs(amplitude) ** 2 for amplitude in self.amplitudes]

    def total_probability(self) -> float:
        return sum(self.probabilities())

    def set_basis(self, index: int) -> None:
        """Collapse onto a computational basis state (deterministic, not a measurement)."""
        if index < 0 or index >= len(self.amplitudes):
            raise ValueError("basis index out of range")
        self.amplitudes = [complex(0.0, 0.0)] * len(self.amplitudes)
        self.amplitudes[index] = complex(1.0, 0.0)

    def apply_matrix(self, matrix: Matrix, targets, controls=()) -> None:
        """Apply `matrix` on `targets`, only where every qubit in `controls` is |1>."""
        targets = list(targets)
        controls = list(controls)
        dimension = 1 << len(targets)
        if len(matrix) != dimension or any(len(row) != dimension for row in matrix):
            raise ValueError("gate matrix dimension does not match target count")
        if not targets:
            raise ValueError("gate needs at least one target")
        for position, qubit in enumerate(targets):
            if qubit < 0 or qubit >= self.qubits:
                raise ValueError("target qubit out of range")
            if qubit in targets[position + 1 :]:
                raise ValueError("duplicate target qubit")
        for control in controls:
            if control < 0 or control >= self.qubits:
                raise ValueError("control qubit out of range")
            if control in targets:
                raise ValueError("control qubit cannot also be a target")

        previous = self.amplitudes
        next_amplitudes = list(previous)
        for base in range(len(previous)):
            if any((base >> qubit) & 1 for qubit in targets):
                continue
            if any(not ((base >> qubit) & 1) for qubit in controls):
                continue

            selected = []
            gathered = []
            for column in range(dimension):
                index = base
                for bit, qubit in enumerate(targets):
                    if (column >> bit) & 1:
                        index |= 1 << qubit
                selected.append(index)
                gathered.append(previous[index])

            for row in range(dimension):
                accumulator = complex(0.0, 0.0)
                for column in range(dimension):
                    accumulator += matrix[row][column] * gathered[column]
                next_amplitudes[selected[row]] = accumulator

        self.amplitudes = next_amplitudes
