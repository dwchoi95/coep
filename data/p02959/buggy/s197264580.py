N=int(input())
a=input().split()
b=input().split()
for i in range(0,N):
  a[i]=int(a[i])
  b[i]=int(b[i])
a[N]=int(a[N])
answer=sum(a)
for i in range(0,N):
    c=b[i]-a[i]
    if c<0:
        a[i]=-c
        b[i]=0
    else:
        a[i]=0
        b[i]=c
    d=b[i]-a[i+1]
    if d<0:
        a[i+1]=-c
        b[i]=0
    else:
        a[i+1]=0
        b[i]=c
print (answer-sum(a))