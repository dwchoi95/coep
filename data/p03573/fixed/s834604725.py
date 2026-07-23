a=list(map(int,input().split()))
for i in a:
    if a.count(i)==1:
        ans=int(i)
print(ans)
