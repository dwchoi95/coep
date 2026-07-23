# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def x(m,n):
    if m== 0:
        return(n+1)
    if n==0:
        return x(m-1,1)
    return x(m-1,x(m,n-1)
    
a,b=input().split(',')
m,n= int(x),int(y)
print()
        