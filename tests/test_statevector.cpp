// SPDX-License-Identifier: MIT
// Unit tests for the QBridge state-vector kernel. Plain assert-based checks so
// that ctest needs no external test framework.

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "qbridge/circuit.hpp"

namespace {

int g_checks = 0;

void expect_close(double actual, double expected, double tolerance, const std::string& label) {
  ++g_checks;
  if (std::fabs(actual - expected) > tolerance) {
    std::cerr << "FAIL " << label << ": expected " << expected << ", got " << actual << "\n";
    std::exit(1);
  }
}

void expect_true(bool condition, const std::string& label) {
  ++g_checks;
  if (!condition) {
    std::cerr << "FAIL " << label << "\n";
    std::exit(1);
  }
}

double distance(const qbridge::StateVector& a, const qbridge::StateVector& b) {
  double worst = 0.0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    worst = std::max(worst, std::abs(a.amplitude(i) - b.amplitude(i)));
  }
  return worst;
}

void test_normalisation_examples() {
  // |0> is normalised and deterministic.
  qbridge::StateVector zero(3);
  expect_close(zero.probability(0), 1.0, 1e-15, "|000> starts in basis 0");
  expect_close(zero.amplitude(5).real(), 0.0, 1e-15, "|000> has no amplitude in |101>");

  // H|0> = (|0> + |1>) / sqrt(2).
  qbridge::StateVector plus(1);
  plus.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  expect_close(plus.amplitude(0).real(), qbridge::kInvSqrt2, 1e-15, "H|0> amplitude |0>");
  expect_close(plus.amplitude(1).real(), qbridge::kInvSqrt2, 1e-15, "H|0> amplitude |1>");
  expect_close(plus.probability(0) + plus.probability(1), 1.0, 1e-15, "H|0> normalisation");

  // X twice is the identity.
  qbridge::StateVector flipped(2);
  const qbridge::Matrix x = qbridge::single_qubit_matrix("x", 0.0);
  flipped.apply_matrix(x, {1});
  expect_close(flipped.probability(2), 1.0, 1e-15, "X|10> = |10> (index 2)");
  flipped.apply_matrix(x, {1});
  expect_close(flipped.probability(0), 1.0, 1e-15, "X X |00> = |00>");
}

void test_bell_state() {
  qbridge::StateVector bell(2);
  bell.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  bell.apply_matrix(qbridge::single_qubit_matrix("x", 0.0), {1}, {0});
  expect_close(bell.probability(0), 0.5, 1e-15, "Bell probability |00>");
  expect_close(bell.probability(3), 0.5, 1e-15, "Bell probability |11>");
  expect_close(bell.probability(1), 0.0, 1e-15, "Bell probability |01> is zero");
  expect_close(bell.probability(2), 0.0, 1e-15, "Bell probability |10> is zero");
  expect_true(std::abs(bell.amplitude(0) - bell.amplitude(3)) < 1e-15,
              "Bell amplitudes are equal (positive branch)");
}

void test_ghz_state() {
  qbridge::StateVector state(3);
  state.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  state.apply_matrix(qbridge::single_qubit_matrix("x", 0.0), {1}, {0});
  state.apply_matrix(qbridge::single_qubit_matrix("x", 0.0), {2}, {1});
  expect_close(state.probability(0), 0.5, 1e-15, "GHZ probability |000>");
  expect_close(state.probability(7), 0.5, 1e-15, "GHZ probability |111>");
  double middle = 0.0;
  for (std::size_t i = 1; i < 7; ++i) middle += state.probability(i);
  expect_close(middle, 0.0, 1e-15, "GHZ has no weight on the other six states");
}

void test_deutsch_jozsa() {
  // Four qubits: three input qubits plus one ancilla prepared in |1>.
  // f(x) = x0 (balanced oracle: CX from q0 into the ancilla).
  qbridge::StateVector state(4);
  const qbridge::Matrix h = qbridge::single_qubit_matrix("h", 0.0);
  const qbridge::Matrix x = qbridge::single_qubit_matrix("x", 0.0);
  state.apply_matrix(x, {3});
  for (int q = 0; q < 4; ++q) state.apply_matrix(h, {q});
  state.apply_matrix(x, {3}, {0});
  for (int q = 0; q < 3; ++q) state.apply_matrix(h, {q});

  // The input register must never be all zeros: every amplitude with the top
  // three bits equal to zero has to vanish.
  const std::size_t input_mask = 0b0111u;  // qubits 0..2
  double zero_input_weight = 0.0;
  for (std::size_t i = 0; i < state.size(); ++i) {
    if ((i & input_mask) == 0) zero_input_weight += state.probability(i);
  }
  expect_close(zero_input_weight, 0.0, 1e-15, "balanced oracle leaves no all-zero input branch");

  // The constant oracle f(x) = 0 must keep the whole weight on the all-zero
  // input branch after the final layer of Hadamards.
  qbridge::StateVector constant(4);
  constant.apply_matrix(x, {3});
  for (int q = 0; q < 4; ++q) constant.apply_matrix(h, {q});
  for (int q = 0; q < 3; ++q) constant.apply_matrix(h, {q});
  double constant_zero_input = 0.0;
  for (std::size_t i = 0; i < constant.size(); ++i) {
    if ((i & input_mask) == 0) constant_zero_input += constant.probability(i);
  }
  expect_close(constant_zero_input, 1.0, 1e-15, "constant oracle keeps the all-zero input branch");
}

void test_swap_and_controlled_phases() {
  qbridge::StateVector state(3);
  state.set_basis(0b101);  // |q2 q1 q0> = |1 0 1>
  state.apply_matrix(qbridge::swap_matrix(), {0, 2});
  expect_close(state.probability(0b101), 1.0, 1e-15, "swap of equal bits keeps the state");

  qbridge::StateVector state2(2);
  state2.set_basis(0b01);  // q0 = 1, q1 = 0
  state2.apply_matrix(qbridge::swap_matrix(), {0, 1});
  expect_close(state2.probability(0b10), 1.0, 1e-15, "swap moves the excitation");

  // CZ only flips the sign of |11>.
  qbridge::StateVector state3(2);
  const qbridge::Matrix h = qbridge::single_qubit_matrix("h", 0.0);
  state3.apply_matrix(h, {0});
  state3.apply_matrix(h, {1});
  state3.apply_matrix(qbridge::single_qubit_matrix("z", 0.0), {1}, {0});
  expect_close(state3.amplitude(0).real(), 0.5, 1e-15, "CZ keeps |00> amplitude");
  expect_close(state3.amplitude(3).real(), -0.5, 1e-15, "CZ flips |11> amplitude");
}

void test_rotation_and_dagger_gates() {
  // Rz(pi/2) equals S up to a global phase e^{-i pi/4}; probabilities match.
  qbridge::StateVector via_rz(1);
  via_rz.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  via_rz.apply_matrix(qbridge::single_qubit_matrix("rz", qbridge::kPi / 2.0), {0});

  qbridge::StateVector via_s(1);
  via_s.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  via_s.apply_matrix(qbridge::single_qubit_matrix("s", 0.0), {0});

  expect_close(via_rz.probability(0), via_s.probability(0), 1e-15, "Rz(pi/2) vs S probability |0>");
  expect_close(via_rz.probability(1), via_s.probability(1), 1e-15, "Rz(pi/2) vs S probability |1>");
  expect_close(std::abs(via_rz.amplitude(1)), std::abs(via_s.amplitude(1)), 1e-15,
               "Rz(pi/2) vs S magnitude");

  // T then T-dagger must return to the original state.
  qbridge::StateVector state(1);
  state.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  state.apply_matrix(qbridge::single_qubit_matrix("t", 0.0), {0});
  state.apply_matrix(qbridge::single_qubit_matrix("tdg", 0.0), {0});
  qbridge::StateVector reference(1);
  reference.apply_matrix(qbridge::single_qubit_matrix("h", 0.0), {0});
  expect_close(distance(state, reference), 0.0, 1e-15, "T followed by T-dagger is the identity");

  // Ry(pi) flips |0> to |1>. The flipped branch is real here, unlike the Y
  // gate which carries the phase factor i.
  qbridge::StateVector ry(1);
  ry.apply_matrix(qbridge::single_qubit_matrix("ry", qbridge::kPi), {0});
  expect_close(ry.probability(1), 1.0, 1e-15, "Ry(pi) maps |0> to |1>");
  expect_close(ry.amplitude(1).real(), 1.0, 1e-15, "Ry(pi) amplitude on |1> is +1");
  expect_close(ry.amplitude(1).imag(), 0.0, 1e-15, "Ry(pi) leaves no imaginary part");

  // A second half turn brings the register back to -|0>, i.e. Ry(pi)^2 = -I.
  ry.apply_matrix(qbridge::single_qubit_matrix("ry", qbridge::kPi), {0});
  expect_close(ry.probability(0), 1.0, 1e-15, "Ry(pi) twice returns to |0>");
  expect_close(ry.amplitude(0).real(), -1.0, 1e-15, "Ry(pi) squared carries the global phase -1");
}

void test_circuit_dsl() {
  const std::string text =
      "# Bell pair\n"
      "qubits 2\n"
      "h 0\n"
      "cx 0 1   // entangle\n";
  const qbridge::Circuit circuit = qbridge::parse_circuit(text, "bell");
  expect_true(circuit.qubits == 2, "DSL reads the qubit count");
  expect_true(circuit.gates.size() == 2, "DSL reads both gates");
  expect_true(circuit.gates[1].name == "cx", "DSL keeps the gate name");
  expect_true(circuit.gates[1].controls.size() == 1 && circuit.gates[1].controls[0] == 0,
              "DSL records the control qubit");

  const qbridge::StateVector state = qbridge::run_circuit(circuit);
  expect_close(state.probability(0), 0.5, 1e-15, "Bell from DSL: |00>");
  expect_close(state.probability(3), 0.5, 1e-15, "Bell from DSL: |11>");

  // Malformed input must be rejected, not silently ignored.
  bool threw = false;
  try {
    qbridge::parse_circuit("h 0\n", "no-qubits");
  } catch (const std::exception&) {
    threw = true;
  }
  expect_true(threw, "DSL rejects a circuit without a qubit count");

  threw = false;
  try {
    qbridge::StateVector bad(2);
    bad.apply_matrix(qbridge::single_qubit_matrix("x", 0.0), {0}, {0});
  } catch (const std::exception&) {
    threw = true;
  }
  expect_true(threw, "kernel rejects a qubit used as both control and target");
}

void test_three_qubit_controlled_gate() {
  qbridge::StateVector state(3);
  const qbridge::Matrix x = qbridge::single_qubit_matrix("x", 0.0);
  // Controls are not satisfied: nothing happens.
  state.apply_matrix(x, {2}, {0, 1});
  expect_close(state.probability(0), 1.0, 1e-15, "ccx does nothing when a control is |0>");
  // Turn both controls on, then the target flips.
  state.apply_matrix(x, {0});
  state.apply_matrix(x, {1});
  state.apply_matrix(x, {2}, {0, 1});
  expect_close(state.probability(0b011), 0.0, 1e-15, "ccx clears |011>");
  expect_close(state.probability(0b111), 1.0, 1e-15, "ccx sets |111>");
}

void test_phase_gates_and_angle_tokens() {
  // P(pi/2)|1> = i|1>, the phase gate acts on the |1> component only.
  qbridge::StateVector phase(1);
  phase.apply_matrix(qbridge::single_qubit_matrix("x", 0.0), {0});
  phase.apply_matrix(qbridge::single_qubit_matrix("p", qbridge::kPi / 2), {0});
  expect_close(phase.amplitude(1).real(), 0.0, 1e-15, "P(pi/2)|1> has no real part");
  expect_close(phase.amplitude(1).imag(), 1.0, 1e-15, "P(pi/2)|1> = i|1>");

  // The DSL accepts `pi/2` style angle tokens for the phase and rotation gates.
  const qbridge::Circuit circuit = qbridge::parse_circuit(
      "qubits 2\n"
      "x 0\n"
      "x 1\n"
      "cp pi/2 0 1\n"
      "rz -pi/4 0\n",
      "angles");
  expect_true(circuit.gates.size() == 4, "DSL reads the angle-token circuit");
  expect_close(circuit.gates[2].theta, qbridge::kPi / 2, 1e-15, "DSL parses cp pi/2");
  expect_close(circuit.gates[3].theta, -qbridge::kPi / 4, 1e-15, "DSL parses rz -pi/4");

  const qbridge::StateVector state = qbridge::run_circuit(circuit);
  // |11> picks up i from the controlled phase and e^{+i pi/8} from rz(-pi/4).
  expect_close(std::abs(state.amplitude(0b11)), 1.0, 1e-15, "cp + rz keep |11> normalised");
  expect_close(state.probability(0b11), 1.0, 1e-15, "cp + rz keep the population on |11>");

  // The shared grammar must reject malformed gates rather than guess an angle.
  bool threw = false;
  try {
    qbridge::parse_circuit("qubits 2\ncp 0 1\n", "missing-angle");
  } catch (const std::exception&) {
    threw = true;
  }
  expect_true(threw, "DSL rejects cp without an angle");
}

}  // namespace

int main() {
  test_normalisation_examples();
  test_bell_state();
  test_ghz_state();
  test_deutsch_jozsa();
  test_swap_and_controlled_phases();
  test_rotation_and_dagger_gates();
  test_circuit_dsl();
  test_three_qubit_controlled_gate();
  test_phase_gates_and_angle_tokens();
  std::cout << "all " << g_checks << " state-vector checks passed\n";
  return 0;
}
