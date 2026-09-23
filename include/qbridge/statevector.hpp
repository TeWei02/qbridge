// SPDX-License-Identifier: MIT
// QBridge — state-vector simulator core (C++17, header-only).
//
// The numeric kernel here is intentionally small and explicit: every gate is
// applied as a dense matrix on the amplitudes indexed by its target qubits,
// using an out-of-place buffer. The Python and JavaScript engines in this
// repository follow the same summation order, so the three implementations
// agree to floating-point rounding (< 1e-12 in the parity checks).

#pragma once

#include <cmath>
#include <complex>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace qbridge {

using Complex = std::complex<double>;
using Matrix = std::vector<std::vector<Complex>>;

constexpr double kPi = 3.14159265358979323846;
constexpr double kInvSqrt2 = 0.70710678118654752440;

inline Matrix identity_matrix(std::size_t dim) {
  Matrix m(dim, std::vector<Complex>(dim, Complex(0.0, 0.0)));
  for (std::size_t i = 0; i < dim; ++i) {
    m[i][i] = Complex(1.0, 0.0);
  }
  return m;
}

inline Complex from_polar(double radius, double angle) {
  return Complex(radius * std::cos(angle), radius * std::sin(angle));
}

// 2x2 matrix for a single-qubit gate. `theta` is used by the rotation gates.
inline Matrix single_qubit_matrix(const std::string& name, double theta) {
  const Complex one(1.0, 0.0);
  const Complex zero(0.0, 0.0);
  const Complex i(0.0, 1.0);

  if (name == "i" || name == "id") return {{one, zero}, {zero, one}};
  if (name == "h") {
    const Complex a(kInvSqrt2, 0.0);
    const Complex b(-kInvSqrt2, 0.0);
    return {{a, a}, {a, b}};
  }
  if (name == "x") return {{zero, one}, {one, zero}};
  if (name == "y") return {{zero, -i}, {i, zero}};
  if (name == "z") return {{one, zero}, {zero, -one}};
  if (name == "s") return {{one, zero}, {zero, i}};
  if (name == "sdg") return {{one, zero}, {zero, -i}};
  if (name == "t") return {{one, zero}, {zero, from_polar(1.0, kPi / 4.0)}};
  if (name == "tdg") return {{one, zero}, {zero, from_polar(1.0, -kPi / 4.0)}};

  // Phase gate: diag(1, exp(i theta)). Controlled versions are built by the
  // executor, which is how `cp` and `cz` are expressed.
  if (name == "p" || name == "u1") {
    return {{one, zero}, {zero, from_polar(1.0, theta)}};
  }

  if (name == "rx" || name == "ry" || name == "rz") {
    const double c = std::cos(theta / 2.0);
    const double s = std::sin(theta / 2.0);
    if (name == "rx") return {{Complex(c, 0.0), Complex(0.0, -s)},
                              {Complex(0.0, -s), Complex(c, 0.0)}};
    if (name == "ry") return {{Complex(c, 0.0), Complex(-s, 0.0)},
                              {Complex(s, 0.0), Complex(c, 0.0)}};
    return {{Complex(std::cos(-theta / 2.0), std::sin(-theta / 2.0)), zero},
            {zero, Complex(std::cos(theta / 2.0), std::sin(theta / 2.0))}};
  }

  throw std::invalid_argument("unknown single-qubit gate: " + name);
}

// 4x4 matrix that swaps the amplitudes of two qubits.
inline Matrix swap_matrix() {
  Matrix m = identity_matrix(4);
  m[1][1] = Complex(0.0, 0.0);
  m[2][2] = Complex(0.0, 0.0);
  m[1][2] = Complex(1.0, 0.0);
  m[2][1] = Complex(1.0, 0.0);
  return m;
}

// Dense state vector of `qubits` qubits, initialised to |0...0>.
class StateVector {
 public:
  static constexpr std::size_t kMaxQubits = 30;

  explicit StateVector(std::size_t qubits)
      : qubits_(qubits), amplitude_(std::size_t(1) << qubits, Complex(0.0, 0.0)) {
    if (qubits == 0 || qubits > kMaxQubits) {
      throw std::invalid_argument("qubit count must be in [1, 30]");
    }
    amplitude_[0] = Complex(1.0, 0.0);
  }

  std::size_t num_qubits() const { return qubits_; }
  std::size_t size() const { return amplitude_.size(); }

  Complex amplitude(std::size_t index) const { return amplitude_.at(index); }

  double probability(std::size_t index) const {
    const Complex a = amplitude_.at(index);
    return std::norm(a);
  }

  std::vector<double> probabilities() const {
    std::vector<double> p(amplitude_.size());
    for (std::size_t i = 0; i < amplitude_.size(); ++i) {
      p[i] = std::norm(amplitude_[i]);
    }
    return p;
  }

  // Collapses the register onto a computational basis state (deterministic;
  // used by tests and by the CLI's --basis option, not a measurement).
  void set_basis(std::size_t index) {
    if (index >= amplitude_.size()) throw std::out_of_range("basis index out of range");
    std::fill(amplitude_.begin(), amplitude_.end(), Complex(0.0, 0.0));
    amplitude_[index] = Complex(1.0, 0.0);
  }

  // Applies a dense `matrix` to the amplitudes selected by `targets`, only on
  // the branches where every qubit in `controls` is |1>.
  void apply_matrix(const Matrix& matrix, const std::vector<int>& targets,
                    const std::vector<int>& controls = {}) {
    const std::size_t dim = std::size_t(1) << targets.size();
    if (matrix.size() != dim || matrix.front().size() != dim) {
      throw std::invalid_argument("gate matrix dimension does not match target count");
    }
    if (targets.empty()) throw std::invalid_argument("gate needs at least one target");
    for (std::size_t a = 0; a < targets.size(); ++a) {
      if (targets[a] < 0 || static_cast<std::size_t>(targets[a]) >= qubits_) {
        throw std::out_of_range("target qubit out of range");
      }
      for (std::size_t b = a + 1; b < targets.size(); ++b) {
        if (targets[a] == targets[b]) throw std::invalid_argument("duplicate target qubit");
      }
    }
    for (int c : controls) {
      if (c < 0 || static_cast<std::size_t>(c) >= qubits_) {
        throw std::out_of_range("control qubit out of range");
      }
      for (int t : targets) {
        if (c == t) throw std::invalid_argument("control qubit cannot also be a target");
      }
    }

    std::vector<Complex> next = amplitude_;
    const std::size_t total = amplitude_.size();
    std::vector<std::size_t> selected(dim, 0);
    std::vector<Complex> gathered(dim, Complex(0.0, 0.0));

    for (std::size_t base = 0; base < total; ++base) {
      bool skip = false;
      for (int t : targets) {
        if ((base >> t) & 1u) {
          skip = true;
          break;
        }
      }
      if (skip) continue;
      bool controls_satisfied = true;
      for (int c : controls) {
        if (!((base >> c) & 1u)) {
          controls_satisfied = false;
          break;
        }
      }
      if (!controls_satisfied) continue;

      for (std::size_t j = 0; j < dim; ++j) {
        std::size_t index = base;
        for (std::size_t b = 0; b < targets.size(); ++b) {
          if ((j >> b) & 1u) index |= std::size_t(1) << targets[b];
        }
        selected[j] = index;
        gathered[j] = amplitude_[index];
      }
      for (std::size_t row = 0; row < dim; ++row) {
        Complex accumulator(0.0, 0.0);
        for (std::size_t col = 0; col < dim; ++col) {
          accumulator += matrix[row][col] * gathered[col];
        }
        next[selected[row]] = accumulator;
      }
    }
    amplitude_.swap(next);
  }

 private:
  std::size_t qubits_;
  std::vector<Complex> amplitude_;
};

}  // namespace qbridge
