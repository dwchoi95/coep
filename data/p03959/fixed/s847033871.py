N=int(input())
T=list(map(int,input().split()))
t=[1]
for i in range(1,N):
    if T[i]!=T[i-1]:
        t.append(1)
    else:
        t.append(T[i])
    if T[i]<T[i-1]:
        print(0)
        exit()
A=list(map(int,input().split()))
A=A[::-1]
a=[1]
for i in range(1,N):
    if A[i]!=A[i-1]:
        a.append(1)
    else:
        a.append(A[i])
    if A[i]<A[i-1]:
        print(0)
        exit()
A=A[::-1]
a=a[::-1]


M=max(A)

for i in range(N):
    if T[i]==M:
        if A[i]==M:
            break
        else:
            print(0)
            exit()

for i in range(N):
    if A[N-1-i]==M:
        if T[N-1-i]==M:
            break
        else:
            print(0)
            exit()
ans=1
mod=(10**9+7)
for i in range(N):
    ans*=min(t[i],a[i])
    ans%=mod
print(ans)