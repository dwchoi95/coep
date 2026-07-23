n = int(input())
bs = list(map(int, input().split()))

res = bs[0]
for i in range(n - 2):
	res += min(bs[i], bs[i + 1])

if n == 2:
	res += bs[-1]
else:
	res += max(bs[-1], bs[-2])

print(res)