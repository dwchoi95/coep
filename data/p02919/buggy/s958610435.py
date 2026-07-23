




N = int(input())
Pn = list(map(int, input().split()))

In = [0] * (N+1)
for i in range(N):
  In[Pn[i]] = i+1
print(Pn)
print(In)

cnt = 0
l = [0] + [i for i in range(N+1)]
r = [i+1 for i in range((N+1))] + [N+1]

for v in range(1, N+1):
  i = In[v]
  
  l1 = l[i]
  l2 = l[l1]
  r1 = r[i]
  r2 = r[r1]
  cnt += ((l1-l2) * (r1-i) + (i-l1) * (r2-r1)) * v
  
  l[r1] = l1
  r[l1] = r1
    
print(cnt)
