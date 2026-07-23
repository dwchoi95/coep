# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def isPrime(num):
    if num<=1:
        return False
    for i in range (2,num):
        if (num % i) == 0:
           return False
        return True
        
m,n=iinput().split(',')
x=int(m[::-1])
y=int(n[::-1])

if(isPrime(x) and isPrime(y)):
    print(x+y)
    
elif(isPrime(x) or isPrime(y)):
    print(int(a)+int(b)
else:
    print(int(a)*int(b)
