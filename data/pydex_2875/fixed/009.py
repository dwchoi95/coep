# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num='A'
n=int(input())
for i in range(1,n+1):
    for j in range (i):
        print('_{}'.format(num),end='')
        num=chr(ord(num)+1)
    num='A'
    print('_')
