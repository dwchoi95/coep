def uq(a,c):
    while(a%c!=0):
        newa=c
        c=a%c
        a=newa
    return c
        

n=(int)(input())

result = 1

for j in range(0,n):
    f=(int)(input())
    result=((result/uq(result,f)))*f
    
print((int)(result))