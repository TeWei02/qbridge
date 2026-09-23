# Deutsch-Jozsa with the constant oracle f(x) = 0.
# Qubits 0-2 hold the input register, qubit 3 is the ancilla.
# A constant oracle keeps all the weight on the all-zero input branch.
qubits 4
x 3
h 0
h 1
h 2
h 3
h 0
h 1
h 2
