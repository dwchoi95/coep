import sys
stdin = sys.stdin
 
sys.setrecursionlimit(10**5) 
 
def li(): return map(int, stdin.readline().split())
def li_(): return map(lambda x: int(x)-1, stdin.readline().split())
def lf(): return map(float, stdin.readline().split())
def ls(): return stdin.readline().split()
def ns(): return stdin.readline().rstrip()
def lc(): return list(ns())
def ni(): return int(stdin.readline())
def nf(): return float(stdin.readline())

from collections import Counter, defaultdict

def compress(s):
    ret = []
    for i, si in enumerate(s):
        if i == 0:
            ret.append(si)
        else:
            if si == ret[-1]:
                continue
            else:
                ret.append(si)
                
    return ret

def removeonly1(s):
    cnt = Counter(s)
    ret = []
    
    for si in s:
        if cnt[si] == 1:
            continue
        else:
            ret.append(si)
            
    return ret

n = ni()
c = [ni() for _ in range(n)]
MOD = 10**9+7

colors = removeonly1(compress(c))


dp = [0 for _ in range(len(colors)+1)]

dp[0] = 1
idxs = defaultdict(list)
keys = set()

for i, ci in enumerate(colors):
    dp[i+1] = dp[i]
    
    if ci in keys:
        dp[i+1] += dp[idxs[ci][-1]+1]
        dp[i+1] %= MOD
        
    idxs[ci].append(i)
    keys.add(ci)
        
print(dp[len(colors)])
    