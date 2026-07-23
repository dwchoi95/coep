def solve():
  n = int(input())
  query = []
  for i in range(n-1):
    c,s,f = (int(i) for i in input().split())
    query.append((c,s,f))

  ans = []
  for i in range(n-1):
    time = 0
    for j in range(i,n-1):
      c,s,f = query[j]
      time = max(s,time)
      if not time%f == 0:
        time += f-time%f
      time += c
    ans.append(time)
  for i in ans:
    print(i)
  print(0)
solve()