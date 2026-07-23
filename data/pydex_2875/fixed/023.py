# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
p='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
n=int(input())
a=0
b='_'
while a<n and n<=26:
    b=b+p[a:a+1]+'_'
    print(b)
    a=a+1