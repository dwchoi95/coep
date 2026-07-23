# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n=str(input())
t=n.split(',')
k=len(t)
i=0
c=0
while i<k:
    a=t[i]
    if len(a).=2 and a[0]==a[len(a)-1]:
        c=c+1
    else:
        c=c
    i=i+1
print(c)