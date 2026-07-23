m = 10 ** 9 + 7
d = {}
r = 1
p = 0
for _ in range(int(input())):
  c = int(input())
  if c == p:
    continue
  if c in d:
    r += d[c]
  r %= m
  d[c] = r
  p = c
