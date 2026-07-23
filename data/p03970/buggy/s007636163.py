s=list(input())
t=list('CODEFESTIVAL2016')
count=0
for k in range(16):
    if s[k] == t[k]:
        count += 1
print(count)

