n = int(input())
a = list(map(int, input().split(" ")))
kisuu = 1
kake = 1
for i in a:
  kake *= 3
  if i % 2 == 0:
    kisuu *= 2
print(kake - kisuu)