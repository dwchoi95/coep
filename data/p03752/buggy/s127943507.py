import copy

N,K = map(int,input().split())
A = list(map(int,input().split()))

ans = [10 ** 12 for i in range(2 ** (N - 1))]
seen = 1  

for i in range(2 ** (N - 1)):
  AA = copy.deepcopy(A)
  cost = 0
  con = 0
  for j in range(N - 1):
    m = max(AA[:j + 1])
    a = AA[j + 1]
    if ((i >> j) & 1) and a <= m:
      cost += (m - a + 1)
      AA[j + 1] = m + 1
      con += 1
    if con == K - 1:
      break
  
  if len([AA[i] for i in range(1,N) if AA[i] > A[0]]) >= K - 1:
    ans[i] = cost
  
print(min(ans))