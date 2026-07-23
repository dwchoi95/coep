N = input()
data = input().split()
bef = -1
count = 0
result = 0

for i in range(len(data)):
	t = int(data[i])
	if bef != t:
		if count > 1:
			result += int(count / 2)
		count = 1
		bef = t
	else:
		count += 1

if count > 1:
	result += int(count / 2)
print(result)