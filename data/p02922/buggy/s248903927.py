a,b = map(int,input().split())
c = 1 + (a-1)
ans = 0
if c <= b:
  ans += 1
  c += (a-1)
print(ans)
  