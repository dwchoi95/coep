# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #

def ack(m,n):
    if m==0:
        return n+1
    elif n==0:
        return ack(m-1,1)
    else:
        return ack(m-1,ack(m,n-1))

m=int(input())
n=int(input())
print ack(m,n)