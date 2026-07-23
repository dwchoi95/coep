# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num=int(input())
for i in range(0,num):
    j=0
    while j<=i:
        print('*', end='')
        j++
    print('\n')
