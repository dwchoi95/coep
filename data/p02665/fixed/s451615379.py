from sys import stdin

a=int(stdin.readline())
A=stdin.readline().split()
sum=0
for k in range(0,a+1):
    sum+=int(A[k])

sum-=int(A[a])
ver=1
lay=1
K=0
T=0

if a==0:
    if A[0]!='1':
        print(-1)
        K=1
    else:
        print(1)
        K=1

for l in range(0,a):
    if lay-int(A[l])<=0:
        print(-1)
        K=1
        break
    if (lay-int(A[l]))*2<int(A[a]) and l==(a-1):
        print(-1)
        K=1
        break
    if (lay-int(A[l]))*2-sum+int(A[l])<=int(A[a]):
        lay=(lay-int(A[l]))*2
        ver+=lay
        sum-=int(A[l])
        T=l
    else:
        lay-=int(A[l])
        sum-=int(A[l])
        x=lay-sum-int(A[a])
        if x==0:
           ver+=lay
        elif x>0:
            print(-1)
            K=1
        else:
           lay=sum+int(A[a])
           ver+=lay
        T=l
        break

if K==0:
    for u in range(T+1,a):
        lay -= int(A[u])
        sum -= int(A[u])
        ver+=lay

if K==0:
    print(ver)