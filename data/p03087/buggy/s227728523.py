N,Q=[int(i) for i in input().split()]
S=input()

c=[0]
t = 0
for i in range(1,N):
   t += 1 if  (S[i-1]=='A' and S[i] == 'C') else 0
   c.append(t)
c.append(t)

for _ in range(Q):
    l,r=[int(x)-1 for x in input().split()]
    print(c[r]-c[l+1])
