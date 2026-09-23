/* QBridge browser demo: runs the JavaScript engine on the reference circuits
 * and shows how far its amplitudes drift from the Python reference.
 */
(function () {
  "use strict";

  var FALLBACK_TOLERANCE = 1e-12;
  var selected = null;
  var reference = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function pad(value, width) {
    var text = String(value);
    while (text.length < width) text = "0" + text;
    return text;
  }

  function basisLabel(index, qubits) {
    return "|" + pad(index.toString(2), qubits) + ">";
  }

  function maxDelta(referenceAmplitudes, state) {
    var worst = 0;
    for (var i = 0; i < referenceAmplitudes.length; i += 1) {
      var amplitude = state.amplitude(i);
      worst = Math.max(worst, Math.abs(referenceAmplitudes[i][0] - amplitude[0]));
      worst = Math.max(worst, Math.abs(referenceAmplitudes[i][1] - amplitude[1]));
    }
    return worst;
  }

  function renderChart(container, probabilities, qubits) {
    container.innerHTML = "";
    for (var index = 0; index < probabilities.length; index += 1) {
      var probability = probabilities[index];

      var row = document.createElement("div");
      row.className = "bar-row";

      var label = document.createElement("span");
      label.className = "bar-label";
      label.textContent = basisLabel(index, qubits);

      var track = document.createElement("div");
      track.className = "bar-track";
      var fill = document.createElement("div");
      fill.className = "bar-fill";
      fill.style.width = (probability * 100).toFixed(4) + "%";
      if (probability > 0.9999) fill.className += " bar-fill-full";
      track.appendChild(fill);

      var value = document.createElement("span");
      value.className = "bar-value";
      value.textContent = probability.toFixed(4);

      row.appendChild(label);
      row.appendChild(track);
      row.appendChild(value);
      container.appendChild(row);
    }
  }

  function renderAmplitudes(state, qubits) {
    var body = byId("amplitude-rows");
    body.innerHTML = "";
    for (var index = 0; index < state.size(); index += 1) {
      var amplitude = state.amplitude(index);
      if (Math.abs(amplitude[0]) < 1e-12 && Math.abs(amplitude[1]) < 1e-12) continue;

      var row = document.createElement("tr");
      var cells = [
        basisLabel(index, qubits),
        amplitude[0].toFixed(10),
        amplitude[1].toFixed(10),
        state.probability(index).toFixed(10)
      ];
      for (var c = 0; c < cells.length; c += 1) {
        var cell = document.createElement("td");
        cell.textContent = cells[c];
        row.appendChild(cell);
      }
      body.appendChild(row);
    }
  }

  function showCircuit(entry) {
    selected = entry;
    var chips = byId("circuit-list").children;
    for (var i = 0; i < chips.length; i += 1) {
      chips[i].className = chips[i].dataset.name === entry.name ? "chip chip-active" : "chip";
    }
    byId("circuit-summary").textContent = entry.summary;
    byId("circuit-source").textContent = entry.source;

    var state = QBridge.runText(entry.source, entry.name);
    renderChart(byId("chart"), state.probabilities(), state.numQubits());
    renderAmplitudes(state, state.numQubits());

    var list = byId("findings");
    list.innerHTML = "";
    for (var f = 0; f < entry.findings.length; f += 1) {
      var item = document.createElement("li");
      item.textContent = entry.findings[f];
      list.appendChild(item);
    }
  }

  function buildChips(circuits) {
    var container = byId("circuit-list");
    container.innerHTML = "";
    circuits.forEach(function (entry) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.textContent = entry.title;
      button.dataset.name = entry.name;
      button.addEventListener("click", function () {
        showCircuit(entry);
      });
      container.appendChild(button);
    });
  }

  function runParityCheck() {
    var tolerance = reference.tolerance || FALLBACK_TOLERANCE;
    var worst = 0;
    var failures = [];
    var list = byId("parity");
    list.innerHTML = "";

    reference.circuits.forEach(function (entry) {
      var state = QBridge.runText(entry.source, entry.name);
      var delta = maxDelta(entry.amplitudes, state);
      worst = Math.max(worst, delta);
      if (delta > tolerance) failures.push(entry.name);

      var item = document.createElement("li");
      item.className = "parity-ok";
      item.textContent = entry.name + " — max |Δamplitude| = " + delta.toExponential(3);
      list.appendChild(item);
    });

    var reported = reference.parity || {};
    ["cpp", "javascript"].forEach(function (engine) {
      var record = reported[engine];
      if (!record) return;
      var item = document.createElement("li");
      if (record.status === "pass") {
        item.className = "parity-ok";
        item.textContent = engine + " engine — max |Δamplitude| = " + Number(record.max_delta).toExponential(3) + " (measured when the reference file was generated)";
      } else {
        item.className = "parity-note";
        item.textContent = engine + " engine — not measured in the run that produced this file";
      }
      list.appendChild(item);
    });

    var status = byId("status");
    if (failures.length === 0) {
      status.className = "status ok";
      status.textContent =
        "parity ok — the JavaScript engine reproduces all " +
        reference.circuits.length +
        " reference circuits (worst |Δamplitude| = " +
        worst.toExponential(3) +
        ", tolerance " +
        tolerance.toExponential(0) +
        ")";
    } else {
      status.className = "status bad";
      status.textContent = "parity mismatch on: " + failures.join(", ");
    }
  }

  function wireCustomCircuit() {
    byId("run-custom").addEventListener("click", function () {
      var source = byId("custom-source").value;
      var error = byId("custom-error");
      error.textContent = "";
      try {
        var state = QBridge.runText(source, "custom");
        renderChart(byId("custom-chart"), state.probabilities(), state.numQubits());
      } catch (exception) {
        byId("custom-chart").innerHTML = "";
        error.textContent = String(exception.message || exception);
      }
    });
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {
        /* offline support is optional; ignore failures on unsupported hosts */
      });
    });
  }

  function boot() {
    wireCustomCircuit();
    registerServiceWorker();
    fetch("reference.json", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("reference.json returned " + response.status);
        return response.json();
      })
      .then(function (payload) {
        reference = payload;
        buildChips(reference.circuits);
        runParityCheck();
        if (reference.circuits.length > 0) showCircuit(reference.circuits[0]);
      })
      .catch(function (exception) {
        var status = byId("status");
        status.className = "status bad";
        status.textContent = "could not load reference.json (" + exception.message + ") — serve this folder over HTTP";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
