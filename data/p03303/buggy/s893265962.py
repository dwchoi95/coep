S = list(input())
w = int(input())

L = len(S)

ans = []

for i in range(0,L,w):
	if i < L-1:
		ans.append(S[i])


print (''.join(ans))