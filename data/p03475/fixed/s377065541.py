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
		n = S[j] - a if a <= S[j] else (a - S[j]) % F[j]
		n = F[j] - n if a > S[j] and n != 0 else n
		
		a = a + C[j] + n
	A.append(a)

for a in A:
	print(a)
print(0)

