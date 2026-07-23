# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
for i in range(1,n+1):
    for j in range(1, i+1):
        if(j==1):
            print('_', end='')
        print(chr(ord('A')-1+j),end='_')
    print()