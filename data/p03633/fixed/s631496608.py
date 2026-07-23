def uq(a,c):
    return c if a%c==0 else uq(c,a%c)

n=(int)(input())

result = 1

for j in range(0,n):
    f=(int)(input())
    result=((result
    
print((int)(result))