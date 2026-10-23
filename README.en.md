# QBridge — Quantum Computing Simulation & Cross-Language Comparison

**Language:** [![English](https://img.shields.io/badge/English-English-blue?style=flat-square)](README.en.md) [![中文](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-%E4%B8%AD%E6%96%87%E7%89%88-blue?style=flat-square)](README.md)

<div align="center">

# Demo Preview

Quantum computing simulation across languages: one `.qc` circuit drives C++17 / Python / JavaScript engines with amplitudes agreeing to 1e-12 (recomputed live in the browser with deviation shown).

<video controls width="640" src="assets/demo-preview.webm"></video>

</div>


[![C++](https://img.shields.io/badge/C%2B%2B-17-%2300599C?logo=c%2B%2B)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Python-3-%233776AB?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The same circuit description file (`.qc`) drives three independent state-vector simulators: a C++17 core, a pure-Python package, and a JavaScript engine that runs directly in the browser. The amplitudes and probabilities of all three must agree to within `1e-12`; this consistency is produced by actual comparison via `scripts/check_parity.py`, not by manual checking.

**Live demo**: <https://tewei02.github.io/qbridge/>
The page loads pre-generated reference results from `docs/reference.json`, recomputes the same batch of circuits in the browser with the JavaScript engine, and displays the deviation between the two on the spot; it remains usable offline through a Service Worker.

## Current Status

Implemented and passing tests:

- C++17 state-vector core: complex amplitudes, single-qubit gates, controlled gates, `ccx`, `swap`, rotation gates
- Python package: `pyproject.toml` builds sdist / wheel directly, with the `qbridge` command-line tool; example circuits are installed with the package (`share/qbridge/circuits/`), so `qbridge --list` has content immediately after `pip install`
- Browser-side JavaScript engine: no CDN, no build step, offline-capable
- Seven demo circuits and cross-engine consistency checks
- CMake + CTest (C++), pytest (Python), ruff (style), GitHub Actions CI

Not yet implemented (planned directions; please do not treat them as current capabilities):

- Noise models and density-matrix simulation (currently ideal state vectors only)
- Real quantum hardware backends; all numbers in this project are ideal simulation results and have never run on any quantum hardware
- GPU acceleration, multithreading
- Circuit-depth optimization, variational workflows for parameterized circuits, measurement sampling statistics (currently outputs exact probabilities)

## Circuit Description Format

```
# Bell pair
qubits 2
h 0
cx 0 1        // entangle
```

Supported gates: `i id h x y z s sdg t tdg p`, `rx ry rz`, `cx cz cp`, `ccx`, `swap`.
Angles can be written as numbers or multiples of pi (`pi/2`, `-pi/4`); content after `#` and `//` is treated as a comment.

## Building & Usage

C++ (requires CMake 3.16+ and a compiler supporting C++17):

```
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/qbridge_cli --list
./build/qbridge_cli --circuit bell --json
```

Python (3.9+, no runtime dependencies):

Install as a package (ships with the seven demo circuits; usable from any directory after install):

```
pip install "qbridge @ git+https://github.com/TeWei02/qbridge.git"   # install directly from the repo
pip install .                                                       # or inside the cloned directory
pip install qbridge                                                 # available after the PyPI release, see "Release"

qbridge --list
qbridge --circuit ghz3
qbridge --circuit bell --json
```

Run from source without installing:

```
PYTHONPATH=python python3 -m qbridge.cli --list
PYTHONPATH=python python3 -m qbridge.cli --circuit ghz3
python3 -m pytest -q
```

JavaScript (macOS's built-in JavaScriptCore is sufficient; no node required):

```
/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc docs/qbridge.js
```

Open the demo page locally:

```
python3 -m http.server --directory docs 8000   # http://localhost:8000
```

## Consistency Verification

```
python3 scripts/gen_reference.py   # recompute docs/reference.json with the Python engine
python3 scripts/check_parity.py    # compare C++ / Python / JavaScript results
```

The seven circuits currently covered (qubits / gates / non-zero amplitudes) with a maximum amplitude deviation of `2.776e-17` across the three engines (tolerance `1e-12`):

| Circuit | Qubits | Gates | Non-zero amplitudes |
| --- | --- | --- | --- |
| `bell` | 2 | 2 | 2 |
| `ghz3` | 3 | 3 | 2 |
| `deutsch_jozsa_balanced` | 4 | 9 | 2 |
| `deutsch_jozsa_constant` | 4 | 8 | 2 |
| `grover2` | 2 | 12 | 1 |
| `qft3` | 3 | 8 | 8 |
| `rotations3` | 3 | 13 | 8 |

## Project Structure

```
circuits/           seven .qc circuits, shared input for the three engines
include/qbridge/    C++ headers (statevector.hpp, circuit.hpp)
src/main.cpp        C++ command-line tool
python/qbridge/     Python engine, parser and CLI
docs/               browser demo (index.html, app.js, qbridge.js, reference.json, PWA assets)
scripts/            reference-file generation, cross-engine comparison, diagram generation
tests/              C++ and Python tests
```

## Release

```
python3 -m build            # produces dist/qbridge-<version>.tar.gz and .whl
```

Tag with a version matching `pyproject.toml` (e.g. `v1.0.0`) and push; `.github/workflows/release.yml` automatically builds, verifies that the wheel contains the demo circuits, smoke-tests the CLI, and publishes via PyPI Trusted Publishing. Before the first release, add a trusted publisher in your PyPI account pointing to this repo's `release.yml` (environment name `pypi`); no API token is needed afterwards.

## License

MIT, author Te-Wei Ko.
