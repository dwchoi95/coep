a, b = map(int, input().split())
cnt = 0
for i in range(a,b+1):
	s = str(i)
	d = s[::-1]
	if s == d:
		cnt += 1
print (cnt)