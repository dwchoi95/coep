s = input()
n = len(s)
sum = [0] * (n + 1)
sum[0] = (s[0] == 'B')
for i in range(1 , n):
	sum[i] = sum[i-1] + (s[i] == 'B')
ans = 0
for i in range(n - 1, 0 ,-1):
	print(i)
	if s[i] == 'W':
		ans += sum[i]
print(ans)
	