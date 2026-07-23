from collections import defaultdict as dd
d = dd(int)
r = 1
p = ""
for _ in range(int(input())):
  c = input()
  if c != p:
    r = (r + d[c]) % (10**9 + 7)
    d[c] = r
  p = c
print(r)