# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def prime(k):
    if k < 1:
        return False
    for i in range(2, k):
        if k % i == 0:
            return False
    return True
    
A, B = input().split(',')
if 1 <= A, B <= 10000:
    X = int(A[::-1])
    Y = int(B[::-1])

    if prime(X) and prime(Y):
        print(X + Y)
    elif prime(X) or prime(Y):
        print(int(A) + int(B))
    else:
        print(int(A) * int(B))