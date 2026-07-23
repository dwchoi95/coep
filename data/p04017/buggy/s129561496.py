import sys
sys.setrecursionlimit(10**7)
INF = 10 ** 18
MOD = 10 ** 9 + 7
from functools import partial, reduce
from operator import mul
prod = partial(reduce, mul)
def LI(): return [int(x) for x in sys.stdin.readline().split()]
def LI_(): return [int(x) - 1 for x in sys.stdin.readline().split()]
def LF(): return [float(x) for x in sys.stdin.readline().split()]
def LS(): return sys.stdin.readline().split()
def II(): return int(sys.stdin.readline())
def SI(): return input()

from bisect import bisect

def main():
    N = II()
    X = LI()  
    X.append(INF)  
    L = II()  
    Q = II()
    AB = []  
    for _ in range(Q):
        AB.append(LI_())
    Unreachs = [[] for _ in range(N)]
    
    for i, x in enumerate(X[:-1]):
        u = bisect(X, x + L)
        Unreachs[i].append(u)
    
    for _ in range(int.bit_length(N - 1) + 1):
        for i in range(N):
            u = Unreachs[Unreachs[i][-1] - 1][-1]
            Unreachs[i].append(u)
    
    for a, b in AB:
        if a > b:
            a, b = b, a
        ans = 0
        while True:
            u = bisect(Unreachs[a], b) - 1
            if u == -1:
                break
            ans += 2 ** u
            a = Unreachs[a][u]
        ans += 1
        print(ans)
    return 0

main()