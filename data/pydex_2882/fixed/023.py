# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def IsPrime(x):
    count=0
    for i in range(1,x+1):
        if (x%i)==0:
            count=count+1
    if count==2:
        return True
    else:
        return False

       
def Reverse(x):
    while x%10==0:
        x=x//10
    rev=0
    while(x!=0):
        r=x%10
        rev=rev*10+r
        x= x//10
    return rev


def decrypt(num1,num2):
    X=Reverse(num1)
    Y=Reverse(num2)
    if IsPrime(X) and IsPrime(Y):
        return X+Y
    elif IsPrime(X) or IsPrime(Y):
        return num1+num2
    else:
        return num1*num2
   
password=input()
dec=password.split(',')
A=int(dec[0])
B=int(dec[1])
print(decrypt(A,B))