/* QBridge — state-vector simulator in plain JavaScript.
 *
 * No dependencies, no CDN, no build step: the same file runs inside the
 * browser demo and under the JavaScriptCore shell (`jsc docs/qbridge.js`) so the
 * JavaScript engine can be checked against the C++ and Python results.
 *
 * Complex numbers are stored as [re, im] pairs because that keeps the hot loop
 * free of object allocations.
 */
(function (root) {
  "use strict";

  var PI = 3.14159265358979323846;
  var INV_SQRT2 = 0.70710678118654752440;
  var VERSION = "1.0.0";

  function complex(re, im) {
    return [re, im];
  }

  function cAdd(a, b) {
    return [a[0] + b[0], a[1] + b[1]];
  }

  function cMul(a, b) {
    return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
  }

  function cAbsSquared(a) {
    return a[0] * a[0] + a[1] * a[1];
  }

  function polar(radius, angle) {
    return [radius * Math.cos(angle), radius * Math.sin(angle)];
  }

  function identityMatrix(dimension) {
    var matrix = [];
    for (var row = 0; row < dimension; row += 1) {
      var line = [];
      for (var column = 0; column < dimension; column += 1) {
        line.push(row === column ? complex(1, 0) : complex(0, 0));
      }
      matrix.push(line);
    }
    return matrix;
  }

  function singleQubitMatrix(name, theta) {
    theta = theta || 0;
    var one = complex(1, 0);
    var zero = complex(0, 0);
    var imaginary = complex(0, 1);

    if (name === "i" || name === "id") return [[one, zero], [zero, one]];
    if (name === "h") {
      var a = complex(INV_SQRT2, 0);
      var b = complex(-INV_SQRT2, 0);
      return [[a, a], [a, b]];
    }
    if (name === "x") return [[zero, one], [one, zero]];
    if (name === "y") return [[zero, [0, -1]], [[0, 1], zero]];
    if (name === "z") return [[one, zero], [zero, [-1, 0]]];
    if (name === "s") return [[one, zero], [zero, imaginary]];
    if (name === "sdg") return [[one, zero], [zero, [0, -1]]];
    if (name === "t") return [[one, zero], [zero, polar(1, PI / 4)]];
    if (name === "tdg") return [[one, zero], [zero, polar(1, -PI / 4)]];
    if (name === "p" || name === "u1") return [[one, zero], [zero, polar(1, theta)]];

    if (name === "rx" || name === "ry" || name === "rz") {
      var cosine = Math.cos(theta / 2);
      var sine = Math.sin(theta / 2);
      if (name === "rx") return [[complex(cosine, 0), complex(0, -sine)], [complex(0, -sine), complex(cosine, 0)]];
      if (name === "ry") return [[complex(cosine, 0), complex(-sine, 0)], [complex(sine, 0), complex(cosine, 0)]];
      return [[complex(Math.cos(-theta / 2), Math.sin(-theta / 2)), zero], [zero, complex(Math.cos(theta / 2), Math.sin(theta / 2))]];
    }

    throw new Error("unknown single-qubit gate: " + name);
  }

  function swapMatrix() {
    var matrix = identityMatrix(4);
    matrix[1][1] = complex(0, 0);
    matrix[2][2] = complex(0, 0);
    matrix[1][2] = complex(1, 0);
    matrix[2][1] = complex(1, 0);
    return matrix;
  }

  function StateVector(qubits) {
    if (qubits < 1 || qubits > 24) throw new Error("qubit count must be in [1, 24]");
    this.qubits = qubits;
    this.amplitudes = [];
    for (var i = 0; i < (1 << qubits); i += 1) this.amplitudes.push(complex(0, 0));
    this.amplitudes[0] = complex(1, 0);
  }

  StateVector.prototype.numQubits = function () {
    return this.qubits;
  };

  StateVector.prototype.size = function () {
    return this.amplitudes.length;
  };

  StateVector.prototype.amplitude = function (index) {
    return this.amplitudes[index];
  };

  StateVector.prototype.probability = function (index) {
    return cAbsSquared(this.amplitudes[index]);
  };

  StateVector.prototype.probabilities = function () {
    var out = [];
    for (var i = 0; i < this.amplitudes.length; i += 1) out.push(cAbsSquared(this.amplitudes[i]));
    return out;
  };

  StateVector.prototype.totalProbability = function () {
    var total = 0;
    for (var i = 0; i < this.amplitudes.length; i += 1) total += cAbsSquared(this.amplitudes[i]);
    return total;
  };

  StateVector.prototype.setBasis = function (index) {
    for (var i = 0; i < this.amplitudes.length; i += 1) this.amplitudes[i] = complex(0, 0);
    this.amplitudes[index] = complex(1, 0);
  };

  StateVector.prototype.applyMatrix = function (matrix, targets, controls) {
    controls = controls || [];
    var dimension = 1 << targets.length;
    if (matrix.length !== dimension) throw new Error("gate matrix dimension does not match target count");
    if (targets.length === 0) throw new Error("gate needs at least one target");
    var a;
    for (a = 0; a < targets.length; a += 1) {
      if (targets[a] < 0 || targets[a] >= this.qubits) throw new Error("target qubit out of range");
      for (var b = a + 1; b < targets.length; b += 1) {
        if (targets[a] === targets[b]) throw new Error("duplicate target qubit");
      }
    }
    for (a = 0; a < controls.length; a += 1) {
      if (controls[a] < 0 || controls[a] >= this.qubits) throw new Error("control qubit out of range");
      for (b = 0; b < targets.length; b += 1) {
        if (controls[a] === targets[b]) throw new Error("control qubit cannot also be a target");
      }
    }

    var previous = this.amplitudes;
    var nextState = previous.slice(0);
    var total = previous.length;
    var selected = [];
    var gathered = [];
    var base;
    var j;

    for (base = 0; base < total; base += 1) {
      var skip = false;
      for (a = 0; a < targets.length; a += 1) {
        if ((base >> targets[a]) & 1) {
          skip = true;
          break;
        }
      }
      if (skip) continue;
      for (a = 0; a < controls.length; a += 1) {
        if (!((base >> controls[a]) & 1)) {
          skip = true;
          break;
        }
      }
      if (skip) continue;

      for (j = 0; j < dimension; j += 1) {
        var index = base;
        for (a = 0; a < targets.length; a += 1) {
          if ((j >> a) & 1) index |= 1 << targets[a];
        }
        selected[j] = index;
        gathered[j] = previous[index];
      }
      for (var row = 0; row < dimension; row += 1) {
        var accumulator = complex(0, 0);
        for (var column = 0; column < dimension; column += 1) {
          accumulator = cAdd(accumulator, cMul(matrix[row][column], gathered[column]));
        }
        nextState[selected[row]] = accumulator;
      }
    }

    this.amplitudes = nextState;
  };

  function stripComment(line) {
    var markers = ["#", "//"];
    for (var i = 0; i < markers.length; i += 1) {
      var position = line.indexOf(markers[i]);
      if (position !== -1) line = line.slice(0, position);
    }
    return line;
  }

  function parseAngle(token) {
    var sign = token.charAt(0) === "-" ? -1 : 1;
    if (token.indexOf("pi") !== -1) {
      var slash = token.indexOf("/");
      if (slash !== -1) return (sign * PI) / parseFloat(token.slice(slash + 1));
      return sign * PI;
    }
    return parseFloat(token);
  }

  var SINGLE_QUBIT_GATES = ["i", "id", "h", "x", "y", "z", "s", "sdg", "t", "tdg"];
  var ROTATION_GATES = ["rx", "ry", "rz"];

  function parseCircuit(text, name) {
    name = name || "circuit";
    var circuit = { name: name, qubits: 0, gates: [] };
    var lines = text.split("\n");
    for (var number = 0; number < lines.length; number += 1) {
      var tokens = stripComment(lines[number]).split(/\s+/).filter(function (token) {
        return token.length > 0;
      });
      if (tokens.length === 0) continue;

      if (tokens[0] === "qubits") {
        if (tokens.length !== 2) throw new Error("circuit '" + name + "' line " + (number + 1) + ": 'qubits' takes exactly one argument");
        circuit.qubits = parseInt(tokens[1], 10);
        if (!(circuit.qubits >= 1 && circuit.qubits <= 30)) {
          throw new Error("circuit '" + name + "' line " + (number + 1) + ": qubit count must be in [1, 30]");
        }
        continue;
      }

      var gate = { name: tokens[0], targets: [], controls: [], theta: 0 };
      if (ROTATION_GATES.indexOf(gate.name) !== -1) {
        if (tokens.length !== 3) throw new Error(gate.name + " expects: <theta> <target>");
        gate.theta = parseAngle(tokens[1]);
        gate.targets = [parseInt(tokens[2], 10)];
      } else if (gate.name === "p") {
        if (tokens.length !== 3) throw new Error("p expects: <theta> <target>");
        gate.theta = parseAngle(tokens[1]);
        gate.targets = [parseInt(tokens[2], 10)];
      } else if (gate.name === "cp") {
        if (tokens.length !== 4) throw new Error("cp expects: <theta> <control> <target>");
        gate.theta = parseAngle(tokens[1]);
        gate.controls = [parseInt(tokens[2], 10)];
        gate.targets = [parseInt(tokens[3], 10)];
      } else if (gate.name === "cx" || gate.name === "cz") {
        if (tokens.length !== 3) throw new Error(gate.name + " expects: <control> <target>");
        gate.controls = [parseInt(tokens[1], 10)];
        gate.targets = [parseInt(tokens[2], 10)];
      } else if (gate.name === "ccx") {
        if (tokens.length !== 4) throw new Error("ccx expects: <control0> <control1> <target>");
        gate.controls = [parseInt(tokens[1], 10), parseInt(tokens[2], 10)];
        gate.targets = [parseInt(tokens[3], 10)];
      } else if (gate.name === "swap") {
        if (tokens.length !== 3) throw new Error("swap expects: <qubit0> <qubit1>");
        gate.targets = [parseInt(tokens[1], 10), parseInt(tokens[2], 10)];
      } else if (SINGLE_QUBIT_GATES.indexOf(gate.name) !== -1) {
        if (tokens.length !== 2) throw new Error(gate.name + " expects: <target>");
        gate.targets = [parseInt(tokens[1], 10)];
      } else {
        throw new Error("circuit '" + name + "' line " + (number + 1) + ": unknown gate '" + gate.name + "'");
      }
      circuit.gates.push(gate);
    }
    if (circuit.qubits === 0) throw new Error("circuit '" + name + "': missing 'qubits' line");
    return circuit;
  }

  function applyGate(state, gate) {
    if (gate.name === "cx") {
      state.applyMatrix(singleQubitMatrix("x"), gate.targets, gate.controls);
    } else if (gate.name === "cz") {
      state.applyMatrix(singleQubitMatrix("z"), gate.targets, gate.controls);
    } else if (gate.name === "cp") {
      state.applyMatrix(singleQubitMatrix("p", gate.theta), gate.targets, gate.controls);
    } else if (gate.name === "ccx") {
      state.applyMatrix(singleQubitMatrix("x"), gate.targets, gate.controls);
    } else if (gate.name === "swap") {
      state.applyMatrix(swapMatrix(), gate.targets, []);
    } else {
      state.applyMatrix(singleQubitMatrix(gate.name, gate.theta), gate.targets, gate.controls);
    }
  }

  function runCircuit(circuit) {
    var state = new StateVector(circuit.qubits);
    for (var i = 0; i < circuit.gates.length; i += 1) applyGate(state, circuit.gates[i]);
    return state;
  }

  function runText(text, name) {
    return runCircuit(parseCircuit(text, name || "circuit"));
  }

  function stateToDict(state, name, engineName) {
    var amplitudes = [];
    var probabilities = state.probabilities();
    for (var i = 0; i < state.size(); i += 1) {
      amplitudes.push([state.amplitude(i)[0], state.amplitude(i)[1]]);
    }
    var support = [];
    for (var j = 0; j < probabilities.length; j += 1) {
      if (probabilities[j] > 1e-12) support.push({ index: j, probability: probabilities[j] });
    }
    return {
      engine: engineName || "javascript",
      circuit: name,
      qubits: state.numQubits(),
      amplitudes: amplitudes,
      probabilities: probabilities,
      support: support
    };
  }

  var QBridge = {
    VERSION: VERSION,
    PI: PI,
    complex: complex,
    singleQubitMatrix: singleQubitMatrix,
    swapMatrix: swapMatrix,
    StateVector: StateVector,
    parseAngle: parseAngle,
    parseCircuit: parseCircuit,
    runCircuit: runCircuit,
    runText: runText,
    stateToDict: stateToDict
  };

  root.QBridge = QBridge;
  if (typeof module !== "undefined" && module.exports) module.exports = QBridge;
})(typeof globalThis !== "undefined" ? globalThis : this);
