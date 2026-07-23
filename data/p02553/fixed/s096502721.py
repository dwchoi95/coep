a,b,c,d = map(int, input().split())
a = [a, b]
b = [c, d]

ans = -float('inf')
for i in a:
  for j in b:
    ans = max(ans, i * j)
print(ans)