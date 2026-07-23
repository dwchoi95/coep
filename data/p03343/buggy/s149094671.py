N, K, Q = map(int, input().split())
A = list(map(int, input().split()))

def find_maximum(y):
  C = [[]]
  for a in A:
    if a < y and len(C[-1]) > 0:
      C.append([])
    else:
      C[-1].append(a)
  cand_x = []
  for Ci in C:
    m = len(Ci)
    if m >= K:
      Ci.sort()
      cand_x += Ci[:m-K+1]
  cand_x.sort()
  if len(cand_x) >= Q and cand_x[0] == y:
    return cand_x[Q-1]
  else:
    return float('inf')

ans = float('inf')
for a in A:
  x = find_maximum(a)
  ans = min(ans, x-a)

print(ans)