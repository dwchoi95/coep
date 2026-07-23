n = int(input())
a = list(map(int, input().split(" ")))
kisuu = 1
kake = 1
for i in a:
  if i != 1:
    kake *= 3
  else:
    kake *= 2
  if i % 2 == 0:
    kisuu *= 2
print(kake - kisuu)