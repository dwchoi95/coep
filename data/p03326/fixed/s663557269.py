[N, M] = map(int, input().split())
a = [list(map(int, input().split())) for i in range(N)]
def value(xyz, sign):
	return sum([xyz[i]*(1 - 2*((sign & (1 << i)) >> i)) for i in range(3)])
print(0 if M == 0 else max([sum([value(a[j], sign) for j in sorted([i for i in range(N)], key = lambda index : value(a[index], sign))[-M:]]) for sign in range(8)]))