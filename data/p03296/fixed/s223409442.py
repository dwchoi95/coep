N = int(input())
a = list(map(int,input().split()))
ans = 0
P = max(a)
for i in range(N-1):
  if a[i+1] == a[i]:
    P += 1
    a[i+1] = P
    ans += 1
print(ans)