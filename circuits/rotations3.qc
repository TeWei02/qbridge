# Mixed single-qubit rotations, phases and entangling gates.
# Used as the "many small gates" case in the three-engine parity check.
qubits 3
h 0
h 1
h 2
rz pi/3 0
rx -pi/5 1
ry pi/7 2
t 0
sdg 1
p pi/8 2
cx 0 2
cz 1 2
ccx 0 1 2
swap 0 1
