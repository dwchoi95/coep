n,m = map(int,input().split())
ab = []
for i in range(n):
	ab.append(list(map(int,input().split())))
    
sab = sorted(ab,key=lambda x:x[0])
cost = 0
for i in sab:
	if m - i[1] > 0:
		m -= i[1]
		cost += i[0] * i[1]
	else:
		for j in range(m):
			cost += i[0]
		break
print(cost)