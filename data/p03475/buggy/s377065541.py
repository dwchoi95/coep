N = int(input())
lines = []

for i in range(N-1):
    lines.append(input())

C = []
S = []
F = []

for line in lines:
	c, s, f = line.split()
	C.append(int(c))
	S.append(int(s))
	F.append(int(f))

A = []

for i in range(N-1):
	a = C[i] + S[i]
	for j in range(i + 1, N - 1):
		
		n = S[j] - a if a <= S[j] else a % F[j]
		a = a + C[j] + n
	A.append(a)

for a in A:
	print(a)
print(0)
