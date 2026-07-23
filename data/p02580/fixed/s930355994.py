import time

t0 = time.time()

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
while 1:
    if j > w:
        break
    if  x[i][1] == ma:
        if (x[i][0],y[j][0]) in s:
            pass
        else:
            if x[i][1]+y[j][1] == ma+mb:
                sw = 1
                break
        i += 1
    else:
        i = 0
        j += 1
    if time.time() - t0 > 2.5:
        break

    
print(ma+mb+sw-1)
