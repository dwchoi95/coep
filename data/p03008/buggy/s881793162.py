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


dp = [0]*(N+1)
for i in range(N+1):
    for j in first_use:
        if i-A[j]>=0:
            dp[i] = max(dp[i-A[j]]+B[j],dp[i])
for i in range(N+1):
    dp[i] = N-i+dp[i]


count = max(dp)
dp = [0]*(count+1)
for i in range(count+1):
    for j in second_use:
        if i-B[j]>=0:
            dp[i] = max(dp[i-B[j]]+A[j],dp[i])
for i in range(N+1):
    dp[i] = count-i+dp[i]

print(max(dp))