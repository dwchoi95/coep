N,K = map(int,input().split())
A = list(map(int,input().split()))

res = float('inf')

for i in range(1<<N):
  a = A[::]
  paint = 0
  cur = 0
  add = 0
  for j in range(N):
    if (i>>j)&1:
      paint += 1
      if a[j] <= cur:
        add += (cur+1) - a[j]
        a[j] = cur+1
      cur = max(cur, a[j])
    else:
      cur = max(cur, a[j])

  if paint == K:
    res = min(res, add)

print(res)