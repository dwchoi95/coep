def cmb(n, r):
    if n - r < r: r = n - r
    if r == 0: return 1
    if r == 1: return n
 
    numerator = [n - r + k + 1 for k in range(r)]
    denominator = [k + 1 for k in range(r)]
 
    for p in range(2,r+1):
        pivot = denominator[p - 1]
        if pivot > 1:
            offset = (n - r) % p
            for k in range(p-1,r,p):
                numerator[k - offset] /= pivot
                denominator[k] /= pivot
 
    result = 1
    for k in range(r):
        if numerator[k] > 1:
            result *= int(numerator[k])
 
    return result
 
list=input().split(" ")
n=int(list[0])
m=int(list[1])
k=int(list[2])
 
niko1=int((n*(n+1)*(2*n+1)/6 - (n+1)*n*(n+1)/2 + n*n*(n+1)/2)/2)
niko2=int((m*(m+1)*(2*m+1)/6 - (m+1)*m*(m+1)/2 + m*m*(m+1)/2)/2)
niko1=niko1%(10**9+7)
niko2=niko2%(10**9+7)
niko1=niko1*m
niko2=niko2*n
niko1=niko1%(10**9+7)
niko2=niko2%(10**9+7)
niko1=niko1*m
niko2=niko2*n
niko1=niko1%(10**9+7)
niko2=niko2%(10**9+7)
niko=niko1+niko2
kosu=cmb(m*n-2, k-2)
kosu=kosu%(10**9+7)
kotae=int(niko*kosu)
kotae=kotae%(10**9+7)

print(kotae)