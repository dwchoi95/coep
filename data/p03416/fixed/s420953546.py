a,b = map(int,input().split())
ans = 0
for i in range(a,b+1):
  s = list(str(i))
  left = s[0:2]
  right = s[3:]
  right.reverse()
  if left == right:
    ans += 1
print(ans)