n = int(input())
maxx, minx, maxy, miny = -10**10, 10**10, -10**10, 10**10
for _ in range(n):
	x, y = map(int, input().split())
	x, y = x+y, x-y
	maxx = max(maxx, x)
	minx = min(minx, x)
	maxy = max(maxy, y)
	miny = min(miny, y)
print(max(maxx - minx, maxy - miny))
