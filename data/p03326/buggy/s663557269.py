[N, M] = map(int, input().split())
a = [list(map(int, input().split())) for i in range(N)]
def value(xyz, sign):
	return sum([xyz[i]*(1 - 2*((sign & (1 << i)) >> i)) for i in range(3)])
print(max([sum([value(a[i], sign) for i in sorted([i for i in range(N)], key = lambda index : value(a[index], sign))[-M:]]) for sign in range(8)]))
