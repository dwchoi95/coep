# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #

def ackermann(m,n):
    m, n= input().split(',')
     if m = 0:
          return (n + 1)
     elif n = 0:
          return ackermann(m - 1, 1)
     else:
          return ackermann(m - 1, ackermann(m, n - 1)) 

ackermann(m,n)