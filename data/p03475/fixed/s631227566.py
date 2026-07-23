import sys
sys.setrecursionlimit(2000)

n = int(input())
lst = []
for _ in range(n - 1):
  lst.append([int(i) for i in input().split()])

def time_cost(i, now, lst):
  if i == n - 1:
    return now
  if now >= lst[i][1]:
    if now % lst[i][2] == 0:
      now += lst[i][0]
    else:
      now += lst[i][0] + lst[i][2] - now % lst[i][2]
  else:
    now = lst[i][1] + lst[i][0]
  return time_cost(i+1, now, lst)

for i in range(n):
  print(time_cost(i, 0, lst))
