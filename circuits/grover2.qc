# Grover search over two qubits with the marked state |11>.
# One oracle call plus one diffusion step rotates the uniform superposition
# onto the marked state with probability 1.
qubits 2
h 0
h 1
cz 0 1
h 0
h 1
x 0
x 1
cz 0 1
x 0
x 1
h 0
h 1
