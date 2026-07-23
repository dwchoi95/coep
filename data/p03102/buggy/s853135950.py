n,m,c=map(int,input().split())
b=list(map(int, input().split()))
u=0
for i in range(n):
    inp=list(map(int,input().split()))
    s=0
    for j in range(m):
        s+=inp[j]*(j+1)
    s+=c
    if s>0:
        u+=1
print(u)