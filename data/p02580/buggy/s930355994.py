h,w,m = map(int,input().split())
H = [0]*(h+1)
W = [0]*(w+1)
s = set([])
for i in range(m):
    a,b = map(int,input().split())
    s.add((a,b))

    H[a] += 1
    W[b] += 1

x = [0]*(h+1)
y = [0]*(w+1)
    
for i in range(h+1):
    x[i] = [i,H[i]]
for i in range(w+1):
    y[i] = [i,W[i]]

x.sort(key= lambda val : val[1],reverse=True)
y.sort(key= lambda val : val[1],reverse=True)

ma = x[0][1]
mb = y[0][1]

i,j = 0,0
sw = 0

xx = x.count(ma)
yy = y.count(mb)

for i in range(xx):
    for j in range(yy):
        if (x[i][0],y[j][0]) not in s:
            sw = 1
            break 
print(ma+mb+sw-1)
