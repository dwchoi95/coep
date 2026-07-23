# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
n=int(input())
i=0
j='_'
while i<n and n<=26:
    j=j+a[i:i+1]+'_'
    print(j)
    i=i+1