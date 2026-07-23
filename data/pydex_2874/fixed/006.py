# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
for i in range (n+1):
    for j in range(i):
        print('*',end='')
    print ()
