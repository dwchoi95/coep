# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=int(input())
if((1<=n) and(n<=26)):
    a=65+n
    for i in range(65,a):
        for j in range(65,i+1):
            print('_{}_'.format(chr(j),end='',)
        print()
else:
    print('n should be between 1 and 26 to print pattern')