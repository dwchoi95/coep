# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = int(input())
c = str('*')
for i in range(1,n+1):
    for j in range(i,2*i):
        t = print(c, end='')
    print('')