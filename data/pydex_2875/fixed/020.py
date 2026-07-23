# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = int(input())

for i in range(1 , n+1):
    print('_',end='')
    a = 65
    for Row in range(1,i+1):
        print(chr(a) + "_",end='')
        a = a+1
    print()