# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = int(input())
a = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'] 
for i in range(n):
    for j in range(i + 1): 
            print('_',(a[j]),sep='',end='')
    print('_')