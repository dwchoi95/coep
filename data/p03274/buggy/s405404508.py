n, k = map(int, input().split())
c = list(map(int, input().split()))
ans = float('Inf')
for i in range(n-k+1):
  l, r = abs(c[i]), abs(c[i+k-1])
  
  if c[i] < 0 and r > 0:
    ans = min(ans, min(l, r) * 2 + max(l, r))
  else:
    ans = min(ans, max(l, r))
print(ans)