// SPDX-License-Identifier: MIT
// QBridge — command line front end for the C++ state-vector simulator.

#include <algorithm>
#include <cstddef>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "qbridge/circuit.hpp"

namespace {

void print_usage() {
  std::cout << "qbridge_cli — state-vector simulator (C++17)\n\n"
               "Usage:\n"
               "  qbridge_cli --list [--dir <circuits>]\n"
               "  qbridge_cli --circuit <name|path> [--dir <circuits>] [--json]\n\n"
               "Options:\n"
               "  --circuit <name|path>  Circuit name inside --dir, or a direct .qc path\n"
               "  --dir <path>           Directory holding .qc files (default: circuits)\n"
               "  --list                 List available .qc circuits\n"
               "  --json                 Emit machine readable JSON (used by parity checks)\n"
               "  --help                 Show this message\n";
}

std::vector<std::string> list_circuits(const std::string& dir) {
  std::vector<std::string> names;
  std::error_code error;
  if (!std::filesystem::is_directory(dir, error)) return names;
  for (const auto& entry : std::filesystem::directory_iterator(dir, error)) {
    if (!entry.is_regular_file()) continue;
    if (entry.path().extension() == ".qc") names.push_back(entry.path().stem().string());
  }
  std::sort(names.begin(), names.end());
  return names;
}

void print_json(const std::string& engine, const qbridge::Circuit& circuit,
                const qbridge::StateVector& state) {
  std::cout << std::setprecision(17);
  std::cout << "{\"engine\":\"" << engine << "\",\"circuit\":\"" << circuit.name << "\",\"qubits\":"
            << circuit.qubits << ",\"amplitudes\":[";
  for (std::size_t i = 0; i < state.size(); ++i) {
    const qbridge::Complex a = state.amplitude(i);
    if (i) std::cout << ",";
    std::cout << "[" << a.real() << "," << a.imag() << "]";
  }
  std::cout << "],\"probabilities\":[";
  const std::vector<double> probabilities = state.probabilities();
  for (std::size_t i = 0; i < probabilities.size(); ++i) {
    if (i) std::cout << ",";
    std::cout << probabilities[i];
  }
  std::cout << "],\"support\":[";
  bool first = true;
  for (std::size_t i = 0; i < probabilities.size(); ++i) {
    if (probabilities[i] <= 1e-12) continue;
    if (!first) std::cout << ",";
    first = false;
    std::cout << "{\"index\":" << i << ",\"probability\":" << probabilities[i] << "}";
  }
  std::cout << "]}\n";
}

void print_human(const qbridge::Circuit& circuit, const qbridge::StateVector& state) {
  std::cout << "circuit: " << circuit.name << "\n"
            << "qubits:  " << circuit.qubits << "\n"
            << "gates:   " << circuit.gates.size() << "\n\n";
  std::cout << std::fixed << std::setprecision(10);
  std::cout << "basis | amplitude (re, im)                          | probability\n";
  std::cout << "------+--------------------------------------------+------------\n";
  const double norm = [&state] {
    double total = 0.0;
    for (double p : state.probabilities()) total += p;
    return total;
  }();
  for (std::size_t i = 0; i < state.size(); ++i) {
    const qbridge::Complex a = state.amplitude(i);
    std::cout << std::setw(5) << i << " | (" << std::setw(12) << a.real() << ", " << std::setw(12)
              << a.imag() << ") | " << std::setw(10) << state.probability(i) << "\n";
  }
  std::cout << "\ntotal probability: " << std::setprecision(15) << norm << "\n";
}

}  // namespace

int main(int argc, char** argv) {
  std::string circuit_argument;
  std::string directory = "circuits";
  bool as_json = false;
  bool list_only = false;

  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if (argument == "--help" || argument == "-h") {
      print_usage();
      return 0;
    } else if (argument == "--list") {
      list_only = true;
    } else if (argument == "--json") {
      as_json = true;
    } else if (argument == "--circuit" && i + 1 < argc) {
      circuit_argument = argv[++i];
    } else if (argument == "--dir" && i + 1 < argc) {
      directory = argv[++i];
    } else {
      std::cerr << "unrecognised argument: " << argument << "\n";
      print_usage();
      return 2;
    }
  }

  if (list_only) {
    for (const std::string& name : list_circuits(directory)) std::cout << name << "\n";
    return 0;
  }
  if (circuit_argument.empty()) {
    print_usage();
    return 2;
  }

  try {
    std::string path = directory + "/" + circuit_argument + ".qc";
    std::error_code error;
    if (!std::filesystem::is_regular_file(path, error)) path = circuit_argument;
    const std::string name = std::filesystem::path(path).stem().string();
    const qbridge::Circuit circuit = qbridge::load_circuit(path, name);
    const qbridge::StateVector state = qbridge::run_circuit(circuit);
    if (as_json) {
      print_json("cpp", circuit, state);
    } else {
      print_human(circuit, state);
    }
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << "\n";
    return 1;
  }
  return 0;
}
