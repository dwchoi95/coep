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

def main():
    tt = t + t
    while len(tt) < len(s): tt += t
    ss = s
    while len(ss) < len(tt) * 2: ss += s
    
    if tt in ss:return -1

    while len(tt) < len(ss): tt += t
    lcp=LcpByZ(tt+"@"+ss)
    
    tn=len(t)
    ans=max(lcp[len(tt):])
    return ans

s=SI()
t=SI()
print(main())

