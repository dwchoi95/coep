N, Q = map(int, input().split())
S = input()
AClst = [0]
c = 0

for i in range(N-1):
  if S[i:i+2]=="AC":
    c += 1
  AClst.append(c)

for q in range(Q):
  l, r = map(int, input().split())
  print(AClst[r-1]-AClst[l-1])