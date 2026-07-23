# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def a(m,n):
    
    if m == 0:
        return n+1
    elif n ==0:
        return a(m-1,1)
    else m>0 and n>0:
        return a(m-1,a(m,n-1))
print(a(1,2))



