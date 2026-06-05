# qbridge — Quantum Computing Bridge (C++/Python)

[![C++](https://img.shields.io/badge/C++-17-%2300599C?logo=c%2B%2B)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Python-3-%233776AB?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A hybrid C++/Python quantum computing simulator and educational tool. The C++ core implements high-performance quantum state simulation, while Python provides the CLI, visualization, and interactive teaching interface.

## Architecture

| Layer | Language | Responsibility |
|-------|----------|----------------|
| Core Simulator | C++17 | State vector, quantum gate application, measurement, Bell states, Deutsch-Jozsa / Grover's algorithm demos |
| Frontend / CLI | Python | Circuit description parsing, calling C++ engine, amplitude/probability visualization, result reporting |

## Key Capabilities

- **State Vector Simulation** — Full complex amplitude representation
- **Quantum Gates** — Hadamard, Pauli (X/Y/Z), CNOT, phase gates
- **Measurement** — Probabilistic state collapse simulation
- **Bell States** — Entanglement demonstration
- **Deutsch-Jozsa Algorithm** — Oracle-based quantum algorithm demo
- **Grover's Search** — Quantum search algorithm demonstration
- **Visualization** — Amplitude and probability distribution plots

## Tech Stack

| Component | Technology |
|-----------|------------|
| Core Engine | C++17 |
| CLI / Viz | Python 3 |
| Math | Eigen (C++), NumPy (Python) |
| Plotting | Matplotlib |

## Installation & Usage

### C++ Core

```bash
mkdir build && cd build
cmake ..
make
./qbridge_core --circuit examples/bell_state.json
```

### Python CLI

```bash
pip install numpy matplotlib
python qbridge_cli.py --circuit examples/deutsch_jozsa.json --visualize
```

### Quick Demo

```bash
# Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2
echo '{"gates": [{"type": "H", "target": 0}, {"type": "CNOT", "control": 0, "target": 1}]}' > /tmp/circuit.json
./build/qbridge_core --circuit /tmp/circuit.json
```

## Project Structure

```
qbridge/
├── src/               # C++ source (quantum gates, measurement, algorithms)
├── include/           # C++ headers
├── python/            # Python CLI and visualization
├── examples/          # Circuit description files
├── tests/             # Unit tests (C++ + Python)
├── CMakeLists.txt
└── README.md
```

## License

MIT
