# QBridge — 量子計算模擬與跨語言對照

[![C++](https://img.shields.io/badge/C%2B%2B-17-%2300599C?logo=c%2B%2B)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Python-3-%233776AB?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

同一份電路描述檔（`.qc`）驅動三個彼此獨立的態向量模擬器：C++17 核心、純 Python 套件、
以及可直接在瀏覽器裡執行的 JavaScript 引擎。三者的振幅與機率必須一致到 `1e-12` 以內，
一致性由 `scripts/check_parity.py` 實際比對產生，不是靠人工核對。

**線上示範**：<https://tewei02.github.io/qbridge/>
頁面載入預先產生的參考結果 `docs/reference.json`，在瀏覽器內用 JavaScript 引擎重算同一批
電路，並當場顯示兩邊的偏差；離線後仍可透過 Service Worker 開啟。

## 目前狀態

已完成並通過測試的部分：

- C++17 態向量核心：複數振幅、單量子位閘、受控閘、`ccx`、`swap`、旋轉閘
- Python 套件（`pip install -e .` 可用）與 `qbridge` 命令列工具
- 瀏覽器端 JavaScript 引擎：無 CDN、無建置步驟、可離線
- 七個示範電路與跨引擎一致性檢查
- CMake + CTest（C++）、pytest（Python）、ruff（風格）、GitHub Actions CI

尚未實作，屬於規劃中的方向（請不要當成現有能力）：

- 雜訊模型與密度矩陣模擬（目前只有理想態向量）
- 真實量子硬體後端；本專案所有數值都是理想模擬結果，沒有跑過任何量子硬體
- GPU 加速、多執行緒
- 電路深度最佳化、參數化電路的變分流程、測量取樣統計（目前輸出的是精確機率）

## 電路描述格式

```
# Bell pair
qubits 2
h 0
cx 0 1        // entangle
```

支援的閘：`i id h x y z s sdg t tdg p`、`rx ry rz`、`cx cz cp`、`ccx`、`swap`。
角度可寫成數字或圓週率倍數（`pi/2`、`-pi/4`）；`#` 與 `//` 之後的內容視為註解。

## 建置與使用

C++（需要 CMake 3.16+ 與支援 C++17 的編譯器）：

```
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/qbridge_cli --list
./build/qbridge_cli --circuit bell --json
```

Python（3.9+，無執行期相依套件）：

```
PYTHONPATH=python python3 -m qbridge.cli --list
PYTHONPATH=python python3 -m qbridge.cli --circuit ghz3
python3 -m pytest -q
```

JavaScript（macOS 內建 JavaScriptCore 即可，不需要 node）：

```
/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc docs/qbridge.js
```

在本機開啟示範頁：

```
python3 -m http.server --directory docs 8000   # http://localhost:8000
```

## 一致性驗證

```
python3 scripts/gen_reference.py   # 用 Python 引擎重算 docs/reference.json
python3 scripts/check_parity.py    # 比對 C++ / Python / JavaScript 三方結果
```

目前涵蓋的七個電路（量子位／閘數／非零振幅數）以及三方最大振幅偏差 `2.776e-17`
（容忍度 `1e-12`）：

| 電路 | 量子位 | 閘數 | 非零振幅 |
| --- | --- | --- | --- |
| `bell` | 2 | 2 | 2 |
| `ghz3` | 3 | 3 | 2 |
| `deutsch_jozsa_balanced` | 4 | 9 | 2 |
| `deutsch_jozsa_constant` | 4 | 8 | 2 |
| `grover2` | 2 | 12 | 1 |
| `qft3` | 3 | 8 | 8 |
| `rotations3` | 3 | 13 | 8 |

## 專案結構

```
circuits/           七個 .qc 電路，三個引擎共用的輸入
include/qbridge/    C++ 標頭（statevector.hpp、circuit.hpp）
src/main.cpp        C++ 命令列工具
python/qbridge/     Python 引擎、解析器與 CLI
docs/               瀏覽器示範（index.html、app.js、qbridge.js、reference.json、PWA 資產）
scripts/            參考檔產生、跨引擎比對、圖示產生
tests/              C++ 與 Python 測試
```

## 授權

MIT，作者 Te-Wei Ko。
