






MOD = int(1e9) + 7
n = int(input())
T = list(map(int, input().split()))
A = list(map(int, input().split()))

Tsa = [0]*n
Asa = [0]*n

if n == 1:
	if T[0] != A[0]:
		print(0)
	else:
		print(1)
elif T[-1] != A[0]:
	print(0)
else:
	
	dai = T[0]
	shou = T[0]
	Tsa[0] = (shou, dai)

	for i in range(1, n):
		if T[i] == dai:
			Tsa[i] = (1, dai)
		else:
			dai = T[i]
			Tsa[i] = (dai, dai)

	
	dai = A[-1]
	shou = A[-1]
	Asa[-1] = (shou, dai)

	for i in reversed(range(-n, -1)):
		if A[i] == dai:
			Asa[i] = (1, dai)
		else:
			dai = A[i]
			Asa[i] = (dai, dai)

	
	ans = 1
	for i in range(n):
		d = max(Tsa[i][0], Asa[i][0])
		u = min(Tsa[i][1], Asa[i][1])

		if d > u:
			ans = 0
			break
		else:
			ans *= u - d + 1
			ans %= MOD
	print(ans)
