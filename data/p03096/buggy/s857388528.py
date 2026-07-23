from collections import defaultdict
from bisect import *
def solve():
    d = defaultdict(lambda: [])
    N = int(input())
    for i in range(N):
        a = int(input())
        d[a].append(i)
    selist = []
    for l in d.values():
        for i in range(len(l)-1):
            if l[i+1]-1>l[i]:
                selist.append([l[i],l[i+1]])
    start_sort = sorted(selist)
    e_ind = {}
    for i,(s,e) in enumerate(start_sort):
        e_ind[e] = i
    ends = list(e_ind.keys())
    ends.sort()
    dp = [0]*(len(selist)+1)
    for i in range(1,len(selist)+1):
        dp[i] = dp[i-1]+1
        ind = bisect_right(ends,selist[i-1][0])
        if ind>0:
            j = e_ind[ends[ind-1]]
            dp[i] += dp[j+1]
    ans = dp[-1]+1
    return ans
print(solve())