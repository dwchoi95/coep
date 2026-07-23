s=input()
t='CODEFESTIVAL2016'

count=0
for num in range(len(s)):
    if s[num] != t[num]:
        count += 1

print(count)
