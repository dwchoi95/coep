n, m = map(int, input().split())
item = input().split()
item = [int(x) for x in item]

item.sort(reverse=True)

s = sum(item)
res = 0
for i in range(n):
  if item[i] > s / (4*m):
    res += 1
    if res >= m:
      print('Yes')
  else:
    print('No')