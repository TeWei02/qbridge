# Deutsch-Jozsa with a balanced oracle f(x) = x0.
# Qubits 0-2 hold the input register, qubit 3 is the ancilla.
# A balanced oracle must leave zero weight on the all-zero input branch.
qubits 4
x 3
h 0
h 1
h 2
h 3
cx 0 3
h 0
h 1
h 2
