N = int(input())
a = list(map(int, input().split()))
ans = 0
count = 1
for i in range(1, len(a)):
	if a[i] == a[i-1]:
		count += 1
		if i == len(a) - 1 and count > 2:
			ans += int(count / 2)
		elif i == len(a) - 1 and count == 2:
			ans += 1
	elif a[i] != a[i-1] and count == 2:
		ans += 1
		count = 1
	elif a[i] != a[i-1] and count > 2:
		ans += count - 2
		count = 1
print(ans)