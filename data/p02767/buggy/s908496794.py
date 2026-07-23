N=int(input())
X=list(map(int,input().split()))
p=sum(X)
ans=0
for i in range(len(X)):
    ans+=(X[i]-p)**2
print(ans)
