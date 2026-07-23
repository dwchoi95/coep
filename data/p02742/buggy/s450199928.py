h,w = [int(i) for i in input().split()]
a = (w + 1) 
n = (h + 1) 
r = a*n
if h % 2 == 0:
    r += (a-1)*n
else:
    r += (a-1)*(n-1)
print(r)