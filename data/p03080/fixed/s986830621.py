N=int(input())
s=input()
n=0
for char in s:
     if char=='R':
         n+=1
     else:
         n+=0
if N/2<n:
    print('Yes')
else:
    print('No')
