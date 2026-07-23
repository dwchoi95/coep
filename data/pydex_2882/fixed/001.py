# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def IsPrime(x):
    p=0
    for i in range(1,x+1):
        if (x%i)==0:
            p=p+1
    if p==2:
        return True
    else:
        return False

       
def Reverse(x):
    while x%10==0:
        x=x//10
    q=0
    while(x!=0):
        r=x%10
        q=q*10+r
        x= x//10
    return q


def decrypt(n1,n2):
    X=Reverse(n1)
    Y=Reverse(n2)
    if IsPrime(X) and IsPrime(Y):
        return X+Y
    elif IsPrime(X) or IsPrime(Y):
        return n1+n2
    else:
        return n1*n2
   
password=input()
dec=password.split(',')
A=int(dec[0])
B=int(dec[1])
print(decrypt(A,B))
