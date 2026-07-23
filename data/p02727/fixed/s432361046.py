X, Y, A, B, C = map(int, input().split())
p = list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))

p.sort(reverse=True)
q.sort(reverse=True)
r.sort(reverse=True)

sa = sum(p[:X])
sb = sum(q[:Y])

p.append(float('inf'))
q.append(float('inf'))


ans = sa + sb
nr = 0
np = X-1
nq = Y-1
while nr < len(r):
  if r[nr] <= min(p[np], q[nq]):
    break
  elif p[np] > q[nq]:
    ans += r[nr] - q[nq]
    nr += 1
    nq -= 1
    continue
  else:
    ans += r[nr] - p[np]
    nr += 1
    np -= 1
    continue

  
print(ans)