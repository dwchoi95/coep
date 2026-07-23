n = int(input())
a = input().split()
count = 0
for i in range(n - 1):
	if a[i] == a[i + 1]:
		if i + 1 < n - 2:
			if a[i] != 1 and a[i + 2] != 1:
				a[i + 1] = 1
				count += 1
			elif a[i] != 2 and a[i + 2] != 2:
				a[i + 1] = 2
				count += 1
			elif a[i] != 3 and a[i + 2] != 3:
				a[i + 1] = 3
				count += 1
		if i == n - 2:
			if a[i] == 1:
				a[i + 1] = 2
				count += 1
				flag = 1
			else:
				a[i + 1] = 1
				count += 1
				flag = 1

print(count)