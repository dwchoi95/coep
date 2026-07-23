N = int(input())
colors = list(input())
before = ""
ans = 0
for color in colors:
  if color != before:
    ans += 1
    before = color
print(ans)
