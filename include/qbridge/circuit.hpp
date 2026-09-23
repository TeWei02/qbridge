// SPDX-License-Identifier: MIT
// QBridge — circuit DSL parser and executor.
//
// The `.qc` text format is shared by the C++, Python and JavaScript engines so
// that all three run literally the same input:
//
//   # comment
//   qubits 3
//   h 0
//   rz 0.7 0
//   cx 0 1
//   ccx 0 1 2
//   swap 0 2

#pragma once

#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "qbridge/statevector.hpp"

namespace qbridge {

struct GateSpec {
  std::string name;
  std::vector<int> targets;
  std::vector<int> controls;
  double theta = 0.0;
};

struct Circuit {
  std::string name;
  int qubits = 0;
  std::vector<GateSpec> gates;
};

inline std::string strip_comment(const std::string& line) {
  std::string out = line;
  const std::size_t hash = out.find('#');
  if (hash != std::string::npos) out = out.substr(0, hash);
  const std::size_t slash = out.find("//");
  if (slash != std::string::npos) out = out.substr(0, slash);
  return out;
}

inline std::vector<std::string> split_tokens(const std::string& line) {
  std::istringstream stream(line);
  std::vector<std::string> tokens;
  std::string token;
  while (stream >> token) tokens.push_back(token);
  return tokens;
}

inline bool is_rotation_gate(const std::string& name) {
  return name == "rx" || name == "ry" || name == "rz";
}

// Angles may be written as plain numbers or as multiples of pi: `pi`, `pi/2`,
// `-pi/4`, `pi/8`. The Python and JavaScript engines accept the same tokens so
// that all three read identical input.
inline double parse_angle(const std::string& token) {
  const std::size_t slash = token.find('/');
  if (token.find("pi") != std::string::npos) {
    const double sign = (!token.empty() && token[0] == '-') ? -1.0 : 1.0;
    if (slash != std::string::npos) return sign * kPi / std::stod(token.substr(slash + 1));
    return sign * kPi;
  }
  return std::stod(token);
}

inline Circuit parse_circuit(const std::string& text, const std::string& name) {
  Circuit circuit;
  circuit.name = name;
  std::istringstream lines(text);
  std::string raw;
  int line_number = 0;
  while (std::getline(lines, raw)) {
    ++line_number;
    const std::vector<std::string> tokens = split_tokens(strip_comment(raw));
    if (tokens.empty()) continue;

    auto fail = [&](const std::string& reason) {
      throw std::runtime_error("circuit '" + name + "' line " + std::to_string(line_number) +
                               ": " + reason);
    };

    if (tokens[0] == "qubits") {
      if (tokens.size() != 2) fail("'qubits' takes exactly one argument");
      circuit.qubits = std::stoi(tokens[1]);
      if (circuit.qubits <= 0 || circuit.qubits > 30) fail("qubit count must be in [1, 30]");
      continue;
    }

    GateSpec gate;
    gate.name = tokens[0];

    if (is_rotation_gate(gate.name)) {
      if (tokens.size() != 3) fail(gate.name + " expects: <theta> <target>");
      gate.theta = parse_angle(tokens[1]);
      gate.targets = {std::stoi(tokens[2])};
    } else if (gate.name == "p") {
      if (tokens.size() != 3) fail("p expects: <theta> <target>");
      gate.theta = parse_angle(tokens[1]);
      gate.targets = {std::stoi(tokens[2])};
    } else if (gate.name == "cp") {
      if (tokens.size() != 4) fail("cp expects: <theta> <control> <target>");
      gate.theta = parse_angle(tokens[1]);
      gate.controls = {std::stoi(tokens[2])};
      gate.targets = {std::stoi(tokens[3])};
    } else if (gate.name == "cx" || gate.name == "cz") {
      if (tokens.size() != 3) fail(gate.name + " expects: <control> <target>");
      gate.controls = {std::stoi(tokens[1])};
      gate.targets = {std::stoi(tokens[2])};
    } else if (gate.name == "ccx") {
      if (tokens.size() != 4) fail("ccx expects: <control0> <control1> <target>");
      gate.controls = {std::stoi(tokens[1]), std::stoi(tokens[2])};
      gate.targets = {std::stoi(tokens[3])};
    } else if (gate.name == "swap") {
      if (tokens.size() != 3) fail("swap expects: <qubit0> <qubit1>");
      gate.targets = {std::stoi(tokens[1]), std::stoi(tokens[2])};
    } else if (gate.name == "i" || gate.name == "id" || gate.name == "h" || gate.name == "x" ||
               gate.name == "y" || gate.name == "z" || gate.name == "s" || gate.name == "sdg" ||
               gate.name == "t" || gate.name == "tdg") {
      if (tokens.size() != 2) fail(gate.name + " expects: <target>");
      gate.targets = {std::stoi(tokens[1])};
    } else {
      fail("unknown gate '" + gate.name + "'");
    }
    circuit.gates.push_back(gate);
  }
  if (circuit.qubits == 0) throw std::runtime_error("circuit '" + name + "': missing 'qubits' line");
  return circuit;
}

inline Circuit load_circuit(const std::string& path, const std::string& name) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open circuit file: " + path);
  std::ostringstream buffer;
  buffer << input.rdbuf();
  return parse_circuit(buffer.str(), name);
}

inline void apply_gate(StateVector& state, const GateSpec& gate) {
  if (gate.name == "cx") {
    state.apply_matrix(single_qubit_matrix("x", 0.0), gate.targets, gate.controls);
  } else if (gate.name == "cz") {
    state.apply_matrix(single_qubit_matrix("z", 0.0), gate.targets, gate.controls);
  } else if (gate.name == "cp") {
    state.apply_matrix(single_qubit_matrix("p", gate.theta), gate.targets, gate.controls);
  } else if (gate.name == "ccx") {
    state.apply_matrix(single_qubit_matrix("x", 0.0), gate.targets, gate.controls);
  } else if (gate.name == "swap") {
    state.apply_matrix(swap_matrix(), gate.targets, {});
  } else {
    state.apply_matrix(single_qubit_matrix(gate.name, gate.theta), gate.targets, gate.controls);
  }
}

inline StateVector run_circuit(const Circuit& circuit) {
  StateVector state(static_cast<std::size_t>(circuit.qubits));
  for (const GateSpec& gate : circuit.gates) apply_gate(state, gate);
  return state;
}

}  // namespace qbridge
