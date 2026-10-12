"""Command line front end: `qbridge` / `python -m qbridge.cli`.

Mirrors the C++ `qbridge_cli` output, including the JSON shape used by the
cross-engine parity checks.
"""

from __future__ import annotations

import argparse
import json
import sysconfig
from pathlib import Path

from . import __version__, circuit, engine


def default_circuit_dir() -> str:
    """範例電路在哪裡。

    直接跑原始碼時是工作目錄下的 `circuits/`；用 pip 安裝時那個目錄不在，
    改找安裝時一併帶進來的 `share/qbridge/circuits/`，這樣
    `pip install qbridge` 之後 `qbridge --list` 就有東西可跑。
    """
    local = Path("circuits")
    if local.is_dir():
        return str(local)
    try:
        installed = Path(sysconfig.get_path("data")) / "share" / "qbridge" / "circuits"
        if installed.is_dir():
            return str(installed)
    except Exception:  # pragma: no cover - 取不到路徑時退回預設值
        pass
    return "circuits"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qbridge",
        description="State-vector simulator (pure Python engine)",
    )
    parser.add_argument("--version", action="version", version=f"qbridge {__version__}")
    parser.add_argument("--circuit", help="circuit name inside --dir, or a direct .qc path")
    parser.add_argument(
        "--dir",
        default=None,
        help="directory holding .qc files (default: ./circuits, falling back to "
        "the example circuits shipped with the package)",
    )
    parser.add_argument("--list", action="store_true", help="list available .qc circuits")
    parser.add_argument("--json", action="store_true", help="emit machine readable JSON")
    return parser


def resolve_circuit(argument: str, directory: str) -> tuple[Path, str]:
    """Resolve `--circuit` to a file path, preferring `<dir>/<name>.qc`."""
    candidate = Path(directory) / f"{argument}.qc"
    if candidate.is_file():
        return candidate, candidate.stem
    direct = Path(argument)
    if direct.is_file():
        return direct, direct.stem
    raise FileNotFoundError(f"no such circuit: {argument}")


def state_to_dict(name: str, state: engine.StateVector, engine_name: str = "python") -> dict:
    """Serialise a final state using the shared cross-engine JSON shape."""
    amplitudes = [[value.real, value.imag] for value in state.amplitudes]
    probabilities = state.probabilities()
    return {
        "engine": engine_name,
        "circuit": name,
        "qubits": state.num_qubits(),
        "amplitudes": amplitudes,
        "probabilities": probabilities,
        "support": [
            {"index": index, "probability": probability}
            for index, probability in enumerate(probabilities)
            if probability > 1e-12
        ],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    directory = arguments.dir or default_circuit_dir()

    if arguments.list:
        for name in sorted(path.stem for path in Path(directory).glob("*.qc")):
            print(name)
        return 0

    if not arguments.circuit:
        build_parser().print_help()
        return 2

    path, name = resolve_circuit(arguments.circuit, directory)
    parsed = circuit.load_circuit(path, name)
    state = circuit.run_circuit(parsed)

    if arguments.json:
        print(json.dumps(state_to_dict(name, state)))
        return 0

    print(f"circuit: {name}")
    print(f"qubits:  {parsed.qubits}")
    print(f"gates:   {len(parsed.gates)}")
    print()
    print("basis | amplitude (re, im)                          | probability")
    print("------+--------------------------------------------+------------")
    for index in range(state.size()):
        value = state.amplitude(index)
        print(
            f"{index:>5} | ({value.real:>12.10f}, {value.imag:>12.10f}) | "
            f"{state.probability(index):>10.10f}"
        )
    print()
    print(f"total probability: {state.total_probability():.15f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
