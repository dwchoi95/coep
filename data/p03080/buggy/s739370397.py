N=int(input())
s=input().split()
y=0
v=0
for i in s:
    if i=='R':
        y+=1
    else:
        v+=1
if y>v:
    print('Yes')
else:
    print('No')