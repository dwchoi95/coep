n = int(input())
bs = list(map(int, input().split()))

res = bs[0]
for i in range(n - 2):
	res += min(bs[i], bs[i + 1])
res += bs[-1]

print(res)