def resolve():
	a, b = map(int, input().split())
	ans = 0
	for i in range(a, b):
		v = str(i)
		d = len(v) 
		if v[:d] == v[d+1:]:
			ans += 1
	print(ans)
resolve()