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
    for i in range(2**N):
        cost_sum = 0
        cnt = 0
        prev_height = 0
        for j in range(N):
            if (i>>j)&1:
                if a[j]<=prev_height:
                    cost_sum += (prev_height+1)-a[j]
                    prev_height += 1
                else:
                    prev_height = a[j]
                cnt += 1
            prev_height = max(a[j], prev_height)
        if cnt>=K:
            ans = min(cost_sum, ans)

    print(ans)

if __name__ == '__main__':
    resolve()