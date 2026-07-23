from collections import defaultdict
from bisect import *
def solve():
    mod = 10**9+7
    d = defaultdict(lambda: [])
    N = int(input())
    for i in range(N):
        a = int(input())
        d[a].append(i)
    selist = []
    ends = [-1]
    for l in d.values():
        for i in range(len(l)-1):
            if l[i+1]-1>l[i]:
                selist.append([l[i],l[i+1]])
                ends.append(l[i+1])
    selist = [[-1,-1]]+sorted(selist,key=lambda x:x[1])
    
    
        
    
    ends.sort()
    dp = [0]*(len(selist))
    for i in range(1,len(selist)):
        dp[i] = dp[i-1]+1
        ind = bisect_right(ends,selist[i][0])
        dp[i] += dp[ind-1]
    ans = dp[-1]+1
    ans %= mod
    return ans
print(solve())