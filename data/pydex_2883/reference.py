def ackmn(m, n):
    '''
    A(0,n)      = n+1
    A(m+1, 0)   = A(m,1)
    A(m+1, n+1) = A(m, A(m+1, n))
    '''
    if m==0:
        return n+1
    if n==0:
        return ackmn(m-1, 1)
    return ackmn(m-1, ackmn(m, n-1))
    
m, n = input().split(',')
m, n = int(m), int(n)

a = ackmn(m, n)
print(a)