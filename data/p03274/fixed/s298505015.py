N, K = map(int, input().split())
lst = list(map(int, input().split()))
ans = 10 ** 10
for i in range(N-K+1):
	left = lst[i]
	right = lst[i+K-1]
	if (abs(left) > abs(right)):
		dis = abs(left - right) + abs(right)
	else:
		dis = abs(left - right) + abs(left)
	if (dis < ans):
		ans = dis    
print(ans)
