def revNum(n):
    ''' reverse and return reverese of a number encoded as string'''
    return int(n[::-1])

def isPrime(n):
    if n == 2:
        return True
    if n == 1:
        return False
    if n % 2 == 0:
        return False
    i = 3
    while (i*i <= n):
        if n % i == 0:
            return False
        i += 2
    return True

def main():
    a, b = input().split(',')
    c, d = revNum(a), revNum(b)
    a, b = int(a), int(b)
    if (isPrime(c)): 
        if (isPrime(d)):
            print(c + d)
        else:
            print(a + b)
    else:
        if (isPrime(d)):
            print(a + b)
        else:
            print(a * b)

main()