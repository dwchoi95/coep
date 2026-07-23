s = input()
count = 0;
anser = "CODEFESTIVAL2016"
for i in range(0,15):
	if not s[i] == anser[i]:
		count+=1
print(count)
