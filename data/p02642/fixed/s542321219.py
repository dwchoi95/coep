import sys
from collections import defaultdict, deque, Counter










stdin = sys.stdin
sys.setrecursionlimit(10 ** 7)
MIN = -10 ** 9
MOD = 10 ** 9 + 7
INF = float("inf")
IINF = 10 ** 18

def main():
    N = int(stdin.readline().rstrip())
    
    A = list(map(int, stdin.readline().rstrip().split()))
    A.sort()
    C = Counter(A)
    cannot = set()
    L= max(A)
    ans = 0
    for a in A:
        if a in cannot: continue
        if C[a] == 1:
            ans += 1
        ind = 1
        while a*ind <= L:
            cannot.add(a*ind)
            ind += 1

    print(ans)

main()
