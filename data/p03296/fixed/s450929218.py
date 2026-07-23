N=int(input())
a=list(map(int,input().split()))
ans=0
for i in range(N-1):
    if a[i]==a[i+1]:
        a[i+1]=10**4+i+1
        ans+=1
print(ans)