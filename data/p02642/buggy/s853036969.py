from collections import Counter as c
n = int(input())
a = list(map(int,input().split()))
a.sort()

count, a_max = 0, a[-1]
li = [-1] * (a_max+1)

for i in a:
  if li[i] == -1:
    count += 1
    li[i] = 0
  li[i] += 1
  j = 2
  while i * j <= a_max:
    li[i*j] = 0
    j += 1

li.sort(reverse=True)
for i in li:
  if i == 1 or i == 0 or i == -1: break
  count -= 1

print(count)