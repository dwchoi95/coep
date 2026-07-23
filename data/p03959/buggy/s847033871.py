N=int(input())
T=list(map(int,input().split()))
A=list(map(int,input().split()))
if T[len(A)-1]!=A[0]:
    print(-1)
else:
        
    t=[1]
    for i in range(1,N):
        if T[i-1]!=T[i]:
            t.append(1)
        else:
            t.append(T[i])
        if T[i-1]>T[i]:
            print(-1)
            exit()
    A=A[::-1]
    a=[1]
    for i in range(1,N):
        if A[i-1]!=A[i]:
            a.append(1)
        else:
            a.append(A[i])
        if A[i-1]>A[i]:
            print(-1)
            exit()
    A=A[::-1]
    a=a[::-1]
    
    ans=1
    for i in range(N):
        ans*=min(t[i],a[i])
        ans%=(10**9+7)
    print(ans)