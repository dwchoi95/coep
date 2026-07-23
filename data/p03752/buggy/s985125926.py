N,K = map(int,input().split())
bills = list(map(int,input().split()))
ans = 0
k = 0
while k < K:
	k = 0
	cost =[]
	cosd = {}
	tatekae = {}
	maxh = 0
	for bi,b in enumerate(bills):
		if b > maxh:
			cost.append(0)
			maxh = b
			k = k + 1
		else:
			c = maxh - b + 1
			cost.append(c)
			maxh2 = maxh + 1
			tatekae[bi] = []
			for b2i,b2 in enumerate(bills[bi:]):
				if maxh2 < b2:
					break
				elif maxh2 == b2:
					c = c + 1
					maxh2 = maxh2 + 1
					tatekae[bi].append(b2i + bi)
			cosd[bi] = c
	if k > K:
		break
	a = min(cosd.items(),key =lambda x: x[1])[0]
	ans = ans + cosd[a]
	bills[a] = bills[a] + cost[a]
	for t in tatekae[a]:
		bills[t] = bills[t] + 1
	k = k + 1
print(ans)