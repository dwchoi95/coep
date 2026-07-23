s = input()

ans = 0

r = 0
p = 0

for j in s:
  if j == 'g':
    r += 1
    if p > 1:
      ans -= p
    p = 0
  else:
    p += 1
    if r > 1:
      ans += r
    r = 0
if p > 1:
  ans -= p
if r > 1:
  ans += r
print (ans)