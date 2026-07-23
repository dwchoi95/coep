import sys
input=sys.stdin.readline

N=int(input())
L=[]
for i in range(N):
    n=int(input())
    L.append(n)
    
dp=[0 for i in range(N)]
dp[0]=1
D=dict()
D[L[0]]=1
for i in range(1,N):
    if L[i] not in D:
        D[L[i]]=1
        dp[i]=dp[i-1]
    else:
        if L[i]==L[i-1]:
            dp[i]=dp[i-1]
        else:
            dp[i]=dp[i-1]+D[L[i]]
            D[L[i]]+=1
print(dp[-1])