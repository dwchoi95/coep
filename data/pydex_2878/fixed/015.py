# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def sumofmarks(lis):
    z=dict()
    for i in lis:
        roll=int(i[0])
        mark=int(i[-1])
        if roll in z:
            z[roll]+= mark
        else:
            y={roll:mark}
            z.update(y)
    return(z)
    
numline=int(input())
x=1
lis=list()
while (x<=numline):
    managein=input()
    lis.append(managein.split(','))
    x+=1
w=(sumofmarks(lis))
Newlis=list()
for i in w:
    a=(i)
    b=(w[i])
    Newlis.append('{}:{}'.format(a,b))
Newlis.sort()
for i in Newlis:
    print(i)
    