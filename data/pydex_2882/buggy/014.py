# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def Checkprime(x):
    digit=0
    for i in range(1,x+1):
        if (x%i)==0:
            digit+=1
    if digit==2:
        return True
    else:
        return False

def reverse(x):
    while x%10==0:
        x=x//10
    rev=0
    while x!=0):
        r=x%10
        rev=rev*10+r
        x= x//10
    return rev


def condition(no1,no2):
    X=reverse(no1)
    Y=reverse(no2)
    if Checkprime(X) and Checkprime(Y):
        return X+Y
    elif Checkprime(X) or Checkprime(Y):
        return no1+no2
    else:
        return no1*no2
A,B=[int(x) for x in input().split(',')]   
print(condition(A,B))

