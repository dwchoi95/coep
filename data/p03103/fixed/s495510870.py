n, m = map(int,input().split())
L = []
ans, cnt = 0, 0
for i in range(n):
  ab = list(map(int,input().split()))
  L.append(ab)
L.sort()
for j in range(n):
  if m-cnt>L[j][1]:
    cnt+=L[j][1]
    ans+=L[j][0]*L[j][1]
  else:
    ans+=L[j][0]*(m-cnt)
    break
print(ans)