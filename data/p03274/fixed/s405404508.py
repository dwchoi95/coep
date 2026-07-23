n, k = map(int, input().split())
c = list(map(int, input().split()))
ans = float('Inf')
for i in range(n-k+1):
  l, r = c[i], c[i+k-1]
  ans = min(abs(l) + abs(r-l), abs(r) + abs(r-l), ans)

print(ans)