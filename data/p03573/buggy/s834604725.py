a=list(map(int,input().split()))
for i in range(2):
    if a.count(a[i])!=1:
        del a[i]
print(int(a[0]))
