N,Q=list(map(int, input().split()))
S=input()

dp=[[0]*2 for _ in range(N)]
if S[0]=='A':
    dp[0][1]=1

for i in range(1,N):
    if S[i]=='C':
        dp[i][0]=dp[i-1][0]+dp[i-1][1]
    elif S[i]=='A':
        dp[i][0]=dp[i-1][0]
        dp[i][1]=1
    else:
        dp[i][0]=dp[i-1][0]


for i in range(Q):
    l,r=list(map(int, input().split()))
    if l==1:
        print(dp[r-1][0]) 
    elif S[l-2]=='A' and S[l-1]=='C':
        print(dp[r-1][0]-dp[l-2][0]-1)
    else:
        print(dp[r-1][0]-dp[l-2][0])