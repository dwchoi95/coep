import sys, itertools
input = lambda: sys.stdin.readline().rstrip() 
sys.setrecursionlimit(10**7)
INF = 10**20
def I(): return int(input())
def F(): return float(input())
def S(): return input()
def LI(): return [int(x) for x in input().split()]
def LI_(): return [int(x)-1 for x in input().split()]
def LF(): return [float(x) for x in input().split()]
def LS(): return input().split()

def resolve():
    N, K = LI()
    a = LI()
    ans = INF
    
    for i in itertools.combinations(range(1, N), K-1):
        cost_sum = 0
        for j, e in enumerate(i):
            cost_sum += (a[0]+j+1)-a[e]
        ans = min(cost_sum, ans)

    print(ans)

if __name__ == '__main__':
    resolve()