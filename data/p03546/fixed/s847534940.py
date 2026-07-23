from collections import defaultdict
h, w = map(int, input().split())
c = []
for i in range(10):
  s = list(map(int, input().split()))
  c.append(s)

a = []
for i in range(h):
  b = list(map(int, input().split()))
  a.append(b)


d = c
for k in range(10):
  for i in range(10):
    for j in range(10):
      d[i][j] = min(d[i][k]+d[k][j], d[i][j])

ans = 0

for i in range(h):
  for j in range(w):
    if a[i][j] == -1:
      continue
    x = a[i][j]
    ans += d[x][1]
print (ans)