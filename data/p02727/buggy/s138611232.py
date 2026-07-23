X,Y,A,B,C = map(int,input().split())
p = list(map(int,input().split()))
q = list(map(int,input().split()))
r = list(map(int,input().split()))
p.sort(reverse=True)
q.sort(reverse=True)
r.sort(reverse=True)
Z = X+Y
P = p[:X]
Q = q[:Y]
R = r[:Z]
ans = 0
if X <= Y:
  S = P + R
  S.sort(reverse=True)
  a = S[:X]
  b = S[X:]
  ans += sum(a)
  T = Q + b
  T.sort(reverse=True)
  c = T[:Y]
  ans += sum(c)
else:
  S = Q + R
  S.sort(reverse=True)
  a = S[:Y]
  b = S[Y:]
  ans += sum(a)
  T = P + b
  T.sort(reverse=True)
  c = T[:X]
  ans += sum(c)
print(ans)
print(a,b)