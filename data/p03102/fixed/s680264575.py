a=tuple(map(int,input().split()))
b=[]
for i in range(a[0]+1):
    b.append(list(map(int,input().split())))
ans=0
s=0
for j in range(a[0]+1)[1:a[0]+1]:
    for k in range(a[1]):
        s+=b[j][k]*b[0][k]
    s+=a[2]
    if s>0:
        ans+=1
    s=0
print(ans)