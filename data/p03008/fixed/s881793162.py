import sys
import math
from collections import defaultdict

sys.setrecursionlimit(10**7)
def input():
    return sys.stdin.readline()[:-1]

mod = 10**9 + 7

def I(): return int(input())
def II(): return map(int, input().split())
def III(): return list(map(int, input().split()))
def Line(N,num):
    if N<=0:
        return [[] for _ in range(num)]
    elif num==1:
        return [I() for _ in range(N)]
    else:
        read_all = [tuple(II()) for _ in range(N)]
        return map(list, zip(*read_all))



def solve():
    N = I()
    A = III()
    B = III()

    first_use = []
    second_use = []
    for i in range(3):
        if A[i]<B[i]:
            first_use.append(i)
        if A[i]>B[i]:
            second_use.append(i)

    def change(n,A,B,use_index):
        dp = [n]*(n+1)
        for i in range(n+1):
            for j in use_index:
                if i-A[j]>=0:
                    dp[i] = max(dp[i-A[j]]+B[j]-A[j],dp[i])
        return dp[n]

    count1 = change(N,A,B,first_use)
    count2 = change(count1,B,A,second_use)

    print(count2)

solve()