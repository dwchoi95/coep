N=int(input())
s=list(input().split())
for i in s:
     n=0
     if i=='R':
         n+=1
if N/2<n:
    print('Yes')
else:
    print('No')