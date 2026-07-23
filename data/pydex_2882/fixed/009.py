# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i1=input()
i2=i1.strip()
i3=i2.split(',')
a=int(i3[0])
b=int(i3[1])
def rev (k):
    s=len(k)-1
    kr=''
    while s>=0:
        kr=kr+k[s]
        s=s-1
    return(kr)
x=int(rev(i3[0]))
y=int(rev(i3[1]))
def prime(p):
    n=int(p)-1
    while n>1:
        if int(p)%n==0:
            st= False
            break
        else:
            st= True  
        n=n-1
    if int(p)==2:
        st= True
    if int(p)==1:
        st= False
    else:
        st=st
    return st
if prime(x) or prime(y):
    if prime(x) and prime(y):
        ou=x+y
    else:
        ou=a+b
else:
    ou=a*b
if a<=10000 and b<=10000 and a>=1 and b>=1:
    print(ou)
    