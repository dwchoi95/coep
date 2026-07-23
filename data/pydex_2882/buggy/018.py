# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #


def Reverse(x):
    while x%10==0:
        x=x//10
        
    Reverse = 0
    while(A > 0):
        Reminder = A %10
        Reverse = (Reverse *10) + Reminder
        Num = Number //10
    return Reverse

def prime(x):
    count=0
    for i in range(1,x+1):
        if(x%i==0):
            count=count+1
        if count==2:
            return true
        else:
            return false

def crypt(x1,x2):
    num1=Reverse(x1)
    num2=Reverse(x2)
    if prime(num1) and prime(num2):
        return num1+num2
    elif:
        prime(num1) and prime(num2):
            return x1+x2
    else:
        return x1*x2
        
password=input()
de=password.split(',')
X=int(de[0])
Y=int(de[1])
print(crypt(X,Y))