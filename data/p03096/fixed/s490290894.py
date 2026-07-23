n=int(input())
cc=[int(input()) for _ in range(n)]


c=[cc[0]]
for i in range(1,n):
    if cc[i]!=cc[i-1]:
        c.append(cc[i])

n=len(c)

right_index=[-1]*n
tmp_right_index=[-1]*(max(c)+1)

for i in range(n):
    if tmp_right_index[c[i]]==-1:
        tmp_right_index[c[i]]=i
    else:
        right_index[i]=tmp_right_index[c[i]]
        tmp_right_index[c[i]]=i

dp=[0]*n
mod=10**9+7

for i in range(n):
    if i==0:
        dp[i]=1
    else:
        if right_index[i]==-1:
            dp[i]+=dp[i-1]%mod
        else:
            dp[i]+=dp[i-1]+dp[right_index[i]]%mod

print(dp[-1]%mod)







    

