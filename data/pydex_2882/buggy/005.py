# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def is Prime(num):
    if num<=1:
        return False
    for i in range(2, num):
        if (num % i) == 0:
            return False
    return True
            
a,b = input().split(',')
x = int(a[::-1])
y = int(b[::-1])

if (isPrime(x) and isPrime(y)):
    print(x+y)

elif (isPrime(x) or isPrime(y)):
    print(int(a)+int(b))
else:
    print(int(a)*int(b))
[1:43 PM, 1/21/2021] Apoorva Mishra: def a(m,n):
    if m == 0:
        return (n + 1)
    if n == 0:
        return a(m-1,1)
    return a(m-1,a(m,n-1))
    
x,y = input().split(',')
m,n = int(x),int(y)
print(a(m,n))