import sys
sys.setrecursionlimit(10**8)
def ii(): return int(sys.stdin.readline())
def mi(): return map(int, sys.stdin.readline().split())
def li(): return list(map(int, sys.stdin.readline().split()))
def li2(N): return [list(map(int, sys.stdin.readline().split())) for i in range(N)]
def dp2(ini, i, j): return [[ini]*i for i2 in range(j)]
def dp3(ini, i, j, k): return [[[ini]*i for i2 in range(j)] for i3 in range(k)]



from itertools import accumulate 

N = ii()
A = li()

acc = list(accumulate(A))


for i in range(N):
    if acc[i] - (acc[-1] - acc[i]) >= 0:
        break

if i == N-1:
    print(abs(A[i] - acc[i-1]))
elif i == 0:
    print(abs(acc[i] - (acc[-1] - acc[i])))
else:
    ans = min(abs(acc[i] - (acc[-1] - acc[i])), abs(acc[i-1] - (acc[-1] - acc[i-1])))
    print(ans)