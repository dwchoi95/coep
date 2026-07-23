N=int(input())
s=list(input().split())
n=0
for i in range(N):
     if i=='R':
         n+=1
     else:
         n+=0
if N/2<n:
    print('Yes')
else:
    print('No')