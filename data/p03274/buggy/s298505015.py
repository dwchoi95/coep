N, K = map(int, input().split())
lst = list(map(int, input().split()))
ans = 2 * 10 ** 5
for i in range(N-K+1):
	k_lst = lst[i:i+K]
	left = min(k_lst)
	right = max(k_lst)
	if (left > right):
		dis = abs(left - right) + abs(right)
	else:
		dis = abs(left - right) + abs(left)
	if (dis < ans):
		ans = dis    
print(ans)
