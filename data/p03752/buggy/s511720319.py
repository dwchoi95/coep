N,K = map(int,input().split())
A = list(map(int,input().split()))

res = float('inf')

for i in range(1<<N):
  a = A[::]
  paint = 0
  cur = None
  add = 0
  for j in range(N):
    if (i>>j)&1:
      paint += 1
      h = a[j]
      if cur is None:
        if j>0 and a[j-1]>=h:
          break
        else:
          cur = h
      else:
        min_h = max(cur, a[j-1])
        if h < min_h:
          add += (min_h+1) - h
          cur = min_h + 1
          a[j] = cur

  if paint == K:
    res = min(res, add)

print(res)
