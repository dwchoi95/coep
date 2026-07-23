# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
I = input()
J = I.strip()
K = J.split(',')
A = int(K[0])
B = int(K[1])

def rev(c):
    s = len(c) - 1
    d = ''
    while s >= 0:
        d = d + c[s]
        s = s - 1
    return(d)

X = int(rev(K[0]))
Y = int(rev(K[1]))

def prime(p):
    n = int(p) - 1
    while n > 1:
        if int(p) % n == 0:
            e = False
            break
        else:
            e = True  
        n = n - 1
    if int(p) == 2:
        e = True
    if int(p) == 1:
        e = False
    else:
        e = e
    return e
if prime(X) or prime(Y):
    if prime(X) and prime(Y):
        f = X + Y
    else:
        f = A + B
else:
    f = A * B
if 1 <= A <= 10000 and 1 <= B <= 10000:
    print(f)