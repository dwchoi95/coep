N=int(input())
L=[]
for i in range(N):
    n=int(input())
    L.append(n)

dp=[0 for i in range(N)]
dp[0]=1
mod=10**9+7
D=dict()
D[L[0]]=1
for i in range(1,N):
    if L[i]==L[i-1]:
        dp[i]=dp[i-1]
    elif L[i] not in D:
        D[L[i]]=dp[i-1]
        dp[i]=dp[i-1]
    else:
        dp[i]=dp[i-1]+D[L[i]]
        dp[i]%=mod
        D[L[i]]=dp[i]
    
print(dp[-1]%mod)
