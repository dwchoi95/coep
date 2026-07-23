# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
num='A'
n=int(input())
for i in range(n+1):
    for j in range (i):
        print('_{}'.format(num),end='')
        num=chr(ord(num)+1)
    print('_'
    num='A'