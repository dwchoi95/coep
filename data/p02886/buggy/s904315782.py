n = int(input())
d = [int(i) for i in input().split()]
s = n * (n-1)

ans = 0
for i in range(n):
  for j in range(s):
      if j < n:
        ans += d[i] * d[j]

print(ans)