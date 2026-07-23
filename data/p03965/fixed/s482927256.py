lis = list(input())
cou = 0
ans = 0
for i in range(len(lis)):
	if lis[i] == "g":
		if cou > 0:
			cou -= 1
			ans += 1
		else:
			cou += 1
	else:
		if cou > 0:
			cou -= 1
		else:
			cou += 1
			ans -= 1
print(max(0,ans))
