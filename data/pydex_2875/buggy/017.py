# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
n=int(input())
k=0
j='_'
while k<n nd n<=26:
    j=j+a[k:k+1]+'_'
    print(j)
    k=k+1