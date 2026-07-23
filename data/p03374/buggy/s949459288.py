n,c = list(map(int,input().split()))

xv = []
go = [0]
goback = [0]
back = [0]
backgo = [0]

mid = 0

for i in range(n):
    xv.append(list(map(int,input().split())))
    if 2*xv[i][0]<= c: mid = i

temp = 0
for i in range(mid+1):
    temp += xv[i][1]
    go.append(temp-xv[i][0])
    goback.append(temp-2*xv[i][0])
temp = 0
for i in range(mid+1,n)[::-1]:
    temp += xv[i][1]
    back.append(temp-(c-xv[i][0]))
    backgo.append(temp-2*(c-xv[i][0]))

print(max(max(go)+max(backgo),max(back)+max(goback)))
