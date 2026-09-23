# Three-qubit quantum Fourier transform applied to the input state |001>.
# Only the final swap is needed here because the input register is read in the
# same bit order the simulator uses.
qubits 3
x 0
h 0
cp pi/2 1 0
cp pi/4 2 0
h 1
cp pi/2 2 1
h 2
swap 0 2
