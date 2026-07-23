N,Q=list(map(int, input().split()))
S=input()


dp=[[False, 0] for _ in range(N+1)]
for i in range(1,N+1):
    if S[i-1]=='A':
        dp[i][0]=True
        dp[i][1]=dp[i-1][1]
    elif S[i-1]=='C':
        dp[i][1]=dp[i-1][1]+int(dp[i-1][0])
    else:
        dp[i][1]=dp[i-1][1]
print(dp)


for i in range(Q):
    l,r=list(map(int, input().split()))
    l-=1
    print(dp[r][1]-dp[l][1]-int(dp[l][0]*(1-dp[l+1][0])))