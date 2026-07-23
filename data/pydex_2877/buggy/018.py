# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=str(input())
x=n.split(',')
k=len(x)
i=0
c=0
while i<k:
    a=x[i]
    if len(a)>=2 and a[0]==a[len(a)-1]:
        c=c+1
        else:
            c=c
        i=1+1
print(c)