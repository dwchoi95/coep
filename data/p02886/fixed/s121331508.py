import copy
x = int(input())
y = list(map(int,input().split()))

result = 0
for (i, v) in enumerate(y):
  z = copy.deepcopy(y)
  c = copy.deepcopy(x) - 1 - i
  r = 0
  for j in range(c):
    r = r + z.pop()
  result = result + r * v

print(result)

