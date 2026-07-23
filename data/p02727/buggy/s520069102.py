X, Y, A, B, C = (int(x) for x in input().split())
R = [int(i) for i in input().split()]
G = [int(i) for i in input().split()]
M = [int(i) for i in input().split()]

print(R, G, M)

R.sort(reverse=True)
G.sort(reverse=True)

for i in range(X):
  M.append(R[i])

for i in range(Y):
  M.append(G[i])

M.sort(reverse=True)

ans = 0
for i in range(X + Y):
  ans = M[i] + ans

print(ans)
