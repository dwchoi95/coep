# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def a(m,n):
    if m == 0:
        return (n + 1)
    if n == 0:
        return a(m-1,1)
    return a(m-1,a(m,n-1))
    
x,y = input().split(',')
m,n = int(x),int(y)
print(a(m,n)