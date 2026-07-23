# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
l = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
i = 0
n = int(input())
if 1<=n<=26:
    for i in range(0,n):
        for j in range(0,i+1):
            print('_'+l[j],end='')
        print('_')

