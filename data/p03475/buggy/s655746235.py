import sys
n=int(input())
c=[]
s=[]
f=[]
if n==1:
    print(0)
    sys.exit()
for i in range(n-1):
    C,S,F=map(int,input().split())
    c.append(C)
    s.append(S)
    f.append(F)
for i in range(n-1):
    tmp=0
    while i<n-1:
        if tmp<=s[i]:
            a=s[i]
        elif tmp%f[i]==0:
            a=s[i]+f[i]
        elif tmp>s[i]:
            b=(tmp-s[i])%f[i]
            a=tmp+b
        tmp=a+c[i]
        i+=1
    print(tmp)
print(0)