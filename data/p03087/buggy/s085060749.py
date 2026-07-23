N, Q = map(int, input().split())
S = input()
AClst = [] 

for i in range(N-1):
  if S[i:i+2]=="AC":
    AClst.append(1)
  else:
    AClst.append(0)
AClst.append(0)

for q in range(Q):
  l, r = map(int, input().split())
  print(AClst[l:r].count(1))