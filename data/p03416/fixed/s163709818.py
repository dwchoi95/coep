def resolve():
	a, b = map(int, input().split())
	ans = 0
	for i in range(a, b+1):
		v = str(i)
		if v == v[::-1]:
			ans += 1
	print(ans)
resolve()