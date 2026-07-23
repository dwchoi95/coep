N=int(input())
s=input()
y=0
v=0
for i in s:
    if i=='R':
        y+=1
    elif i=='B':
        v+=1
if y>v:
    print('Yes')
elif v>=y:
    print('No')