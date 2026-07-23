N,K = map(int,input().split())
x = list(map(int,input().split()))
ans=float("inf")

for i in range(K):
    if i + K >= N+1:
        break
    else:
        a = min(abs(x[K+i-1]),abs(x[i])) 
        ans = min(ans,x[K+i-1]-x[i]+a)
print(ans)
