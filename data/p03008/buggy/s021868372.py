import sys
input = sys.stdin.readline

n = int(input())
a1, a2, a3 = map(int, input().split())
b1, b2, b3 = map(int, input().split())
def f(n, a1, a2, a3, b1, b2, b3):
  dp = [0]*(n+1)
  for i in range(n+1):
    for a, b in zip((a1, a2, a3), (b1, b2, b3)):
      if i-a >= 0:
        dp[i] = max(dp[i], dp[i-a]+b)
  return max(dp)
m = f(n, a1, a2, a3, b1, b2, b3)
ans = f(m, b1, b2, b3, a1, a2, a3)
print(ans)