n,q=map(int,input().split())
s=input()+'Z'
A=[0]*(n+1)
cnt=0
for i in range(n):
    A[i]=cnt
    if s[i]=='A' and s[i+1]=='C':
        cnt+=1
ANS=[]
for i in range(q):
    l,r=map(int,input().split())
    ANS.append(A[r-1]-A[l-1])
for ans in ANS:
    print(ans)