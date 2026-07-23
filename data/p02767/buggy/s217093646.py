n=int(input())
x=list(map(int,input().split()))
ans=sum(x)
print(ans)
v=0
for i in x:
    v+=(i-ans)**2
print(v)
