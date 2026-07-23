import sys

sys.setrecursionlimit(10 ** 6)
int1 = lambda x: int(x) - 1
p2D = lambda x: print(*x, sep="\n")
def II(): return int(sys.stdin.readline())
def MI(): return map(int, sys.stdin.readline().split())
def LI(): return list(map(int, sys.stdin.readline().split()))
def LLI(rows_number): return [LI() for _ in range(rows_number)]
def SI(): return sys.stdin.readline()[:-1]

def LcpByZ(target):
    len_t = len(target)
    lcp = [-1] * len_t
    top = 1  
    left = 0  
    right = 0  
    lcp[0] = 0
    while top < len_t:
        
        while top + right < len_t and target[right] == target[top + right]:
            right += 1
        
        lcp[top] = right
        left = 1
        
        if right == 0:
            top += 1
            continue
        
        while left + lcp[left] < right and left < right:
            lcp[top + left] = lcp[left]
            left += 1
        
        top += left
        right -= left
        left = 0  
    return lcp

def dfs(i,si):
    dp[i]=0
    ni=(i+tn)%sn
    if lcp[tn+1+ni]!=tn:return False
    if ni==si:return True
    if dp[ni]==-1 and dfs(ni,si):return True
    dp[i]=dp[ni]+1

s=SI()
t=SI()
ss = s
while len(ss) < len(s) + len(t): ss += s
lcp = LcpByZ(t + "@" + ss)
sn = len(s)
tn = len(t)
dp=[-1]*sn
for i in range(sn):
    if dp[i]!=-1:continue
    if dfs(i,i):
        print(-1)
        exit()
print(max(dp))
