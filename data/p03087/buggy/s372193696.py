n,q=map(int,input().split())
s=input()
V=[0]*n
X=[]
for i in range(q):
    l,r=map(int,input().split())
    X.append([l,r])

for i in range(n-1):
    if s[i:i+2]=='AC':
        V[i]+=1

for i in range(q):
    ans=sum(V[X[i][0]-1:X[i][1]])
    if V[X[i][1]-1]==1:
        ans-=1
print(ans)