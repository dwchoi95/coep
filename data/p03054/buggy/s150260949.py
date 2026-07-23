h,w,n=[int(j) for j in input().split()]
r,c=[int(j) for j in input().split()]
s=input()
t=input()


x=c
for i in range(n):
    if s[i]=="R":
        x+=1
    if t[i]=="L" and x>1:
        x-=1
if not 1<=x<=w:
    print("NO")
    exit()


x=c
for i in range(n):
    if s[i]=="L":
        x-=1
    if t[i]=="R" and x<w:
        x+=1
if not 1<=x<=w:
    print("NO")
    exit()


x=r
for i in range(n):
    if s[i]=="U":
        x+=1
    if t[i]=="D" and x>1:
        x-=1
if not 1<=x<=h:
    print("NO")
    exit()


x=r
for i in range(n):
    if s[i]=="D":
        x-=1
    if t[i]=="U" and x<h:
        x+=1
if not 1<=x<=h:
    print("NO")
    exit()
print("YES")