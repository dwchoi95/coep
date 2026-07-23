n = int(input())
g1,s1,b1 = map(int,input().split())
g2,s2,b2 = map(int,input().split())
def trade(n,g1,s1,b1,g2,s2,b2):
  tradelist = []
  for x,y in (g1,g2),(s1,s2),(b1,b2):
    if x < y:
      tradelist.append((x,y))
  if not tradelist:
    return n
  dp = [0]*(n+1)
  for w,v in tradelist:
    for i in range(n+1-w):
      dp[i+w] = max(dp[i+w],dp[i]+v)
  ptr = n
  ret = dp[n]
  while ptr and dp[ptr-1] == dp[n]:
    ret += 1
    ptr -= 1
  return ret

ans1 = trade(n,g1,s1,b1,g2,s2,b2)
ans2 = trade(ans1,g2,s2,b2,g1,s1,b1)
print(ans2)