import sys
input = sys.stdin.readline
N, K, Q = map(int, input().split())
a = list(map(int, input().split()))
ta = a + []
res = pow(10, 10)
for x in sorted(a):
  
  t = sorted(ta)
  if t[Q - 1] == pow(10, 10): break
  res = min(res, t[Q - 1] - t[0])
  for i in range(N):
    if a[i] == x:
      for j in range(i - K + 1, i + K):
        if j in range(N):
          ta[j] = pow(10, 10)
print(res)